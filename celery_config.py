from scheduler import settings

broker_url = settings.queue_uri
result_backend = f"rpc://{settings.queue_uri}"

task_serializer = "pickle"
result_serializer = "pickle"
event_serializer = "json"
accept_content = ["application/json", "application/x-python-serialize"]
result_accept_content = ["application/json", "application/x-python-serialize"]
