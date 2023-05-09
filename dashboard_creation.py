import json
import boto3

def lambda_handler(event, context):
    print(event)
    client = boto3.client('cloudwatch')
    
    environment_name = event['detail']['EnvironmentName']
    region = event['region']
   
    if event['detail']['Status'] == 'Instance added':
        instance_ids = [instance.strip() for instance in event['detail']['Message'].split('[', 1)[1].split(']')[0].split(',')]
    
        dashboard_name = f'{environment_name}-dashboard'
        try:
            response = client.get_dashboard(DashboardName=dashboard_name)
            dashboard_body = json.loads(response['DashboardBody'])
        except client.exceptions.ResourceNotFound:
            dashboard_body = {"widgets": []}
    
        cpu_widget_exists = False
        cpu_widget_index = None
        for i, widget in enumerate(dashboard_body["widgets"]):
            if widget.get("properties", {}).get("title") == "CPUUtilization - All Instances":
                cpu_widget_exists = True
                cpu_widget_index = i
                
                metrics = widget["properties"]["metrics"]
                
                new_metrics = [
                    [
                        "AWS/EC2",
                        "CPUUtilization",
                        "InstanceId",
                        instance_id
                    ] for instance_id in instance_ids
                ]
                metrics += new_metrics
                
                widget["properties"]["metrics"] = metrics
                break
    
        if not cpu_widget_exists:
            
            cpu_metrics = [[
                "AWS/EC2",
                "CPUUtilization",
                "InstanceId",
                instance_id
            ] for instance_id in instance_ids]
            
            cpu_widget = {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": cpu_metrics,
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "stat": "Average",
                    "period": 60,
                    "title": "CPUUtilization - All Instances"
                }
            }
            dashboard_body["widgets"].append(cpu_widget)
    
        # create widgets for network metrics of each instance
        network_widgets = []
        for instance_id in instance_ids:
            network_metric = [
                "AWS/EC2",
                "NetworkIn",
                "InstanceId",
                instance_id
            ]
            network_widget = {
                "type": "metric",
                "x": 0,
                "y": len(network_widgets),
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [network_metric],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "stat": "Average", 
                    "period": 60, 
                    "title": f"NetworkIn - {instance_id}"
                }
            }
            network_widgets.append(network_widget)
    
        
        dashboard_body["widgets"] += network_widgets
    
        response = client.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)
        )

    elif event['detail']['Status'] == 'Instance removed':
        instance_id = event['detail']['Message'].split('[', 1)[1].split(']')[0]
        
        dashboard_name = f'{environment_name}-dashboard'
        try:
            response = client.get_dashboard(DashboardName=dashboard_name)
            dashboard_body = json.loads(response['DashboardBody'])
        except client.exceptions.ResourceNotFound:
            dashboard_body = {"widgets": []}
        
        for i, widget in enumerate(dashboard_body["widgets"]):
            if widget.get("properties", {}).get("title") == "CPUUtilization - All Instances":
                metrics = widget["properties"]["metrics"]
                updated_metrics = [metric for metric in metrics if instance_id not in metric]
                
                if updated_metrics:
                    widget["properties"]["metrics"] = updated_metrics
                else:
                    # Remove widget if no instances remain
                    del dashboard_body["widgets"][i]
                break
        
        for i, widget in enumerate(dashboard_body["widgets"]):
            if widget.get("properties", {}).get("title") == f"NetworkIn - {instance_id}":
                del dashboard_body["widgets"][i]
                break
        
        response = client.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)
        )    
        
    elif event['detail']['Status'] == 'Environment termination successful':
        dashboard_name = f'{environment_name}-dashboard'
        response = client.delete_dashboards(
            DashboardNames=[dashboard_name]
        )
        print(f'Dashboard {dashboard_name} deleted successfully.')
        
    else:
        print('Code execution error')
        
    return response
