import os
import json
import zipfile
from google.cloud import storage
from google.cloud import dialogflowcx_v3beta1 as dialogflow

def export_agent(project_id, location, agent_id, bucket_name):
    
    #client options need to be passed for non-global endpoints
    #client_options = {"api_endpoint": "us-east1-dialogflow.googleapis.com"}
    #client = dialogflow.AgentsClient(client_options=client_options)
    
    client = dialogflow.AgentsClient()
    storage_client = storage.Client()

    agent_path = client.agent_path(project_id, location, agent_id)
    
    export_request = dialogflow.ExportAgentRequest(
        name=agent_path,
        agent_uri=f"gs://{bucket_name}/agent.zip",
        data_format=dialogflow.ExportAgentRequest.DataFormat.JSON_PACKAGE,
    )

    operation = client.export_agent(request=export_request)
    operation.result()
    print(f"Agent exported to gs://{bucket_name}/agent.zip")

def restore_agent(agent_id, gcs_bucket_name, gcs_file_path, project_id, location):
    # Define the client and agent path
    client = dialogflow.AgentsClient()
    agent_path = client.agent_path(project=project_id, location=location, agent=agent_id)
    
    # Specify the URI to the GCS file
    gcs_uri = f"gs://{gcs_bucket_name}/{gcs_file_path}"

    # Create the restore request
    request = dialogflow.RestoreAgentRequest(
        name=agent_path,
        agent_uri=gcs_uri
    )
    
    
    # Restore the agent
    operation = client.restore_agent(request=request)
    print("Restoring agent...")

    # Wait for the operation to complete
    response = operation.result()
    print("Agent restored successfully:", response)

    #https://us-central1-custom-ccai-deliverables-dev.cloudfunctions.net/cxPrebuiltAgentsPaymentArrangement_1


def unzip_agent(gcs_bucket_name,gcs_agent_filePath):
    
    storage_client = storage.Client()

    bucket = storage_client.bucket(gcs_bucket_name)

    blob = bucket.blob(gcs_agent_filePath)

    blob.download_to_filename("./workdir/agentforupdate.zip")

    with zipfile.ZipFile("./workdir/agentforupdate.zip", "r") as zip_ref:
        zip_ref.extractall("workdir/agent")


def modify_webhooks(webhook_path, environment_key):
    environments = {
        "UAT": "www.test-uat.com",
        "PROD": "www.test-prod.com"
    }

    for root, _, files in os.walk(webhook_path):
        for file in files:
            data = None
            if file.endswith(".json"):
                file_path = os.path.join(root,file)
                with open(file_path, "r") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        print(f"Skipping invalid JSON file: {file_path}")
                        continue
                url = data.get("genericWebService", {}).get("uri") 
                
                if url:
                    new_url = url.replace("www.test-dev.com", environments[environment_key])
                    data["genericWebService"]["uri"] = new_url
                
                with open(file_path, "w") as f:
                    json.dump(data,f,indent=2)
                    print("webook url updated")

def rezip_agent(agent_source_path, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(agent_source_path):
            for file in files:
                print(os.path.join(root, file), os.path.relpath(os.path.join(root, file)))
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file)))
    print("zip completed")

def upload_agent_to_gcs(agent_zip_file_path, bucket_name, destination_file_name):
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_file_name)

    blob.upload_from_filename(agent_zip_file_path)

    print("agent uploaded")


if __name__ == "__main__":

    project_id = "andygproj"
    location="global"

    #global agent
    agent_id="bb117701-a498-4b7e-a5f9-8321ec2c02c9"

    bucket_name = "df-devops-xys"

    #tagrget path projects/andygproj/locations/global/agents/6cc82f61-9529-471d-8092-4644fd42c582

    target_agent_id="8b0658d0-a0e6-47c8-ac78-abf70b5b8bdw"

    #export_agent(project_id, location, agent_id, bucket_name)
    unzip_agent(bucket_name, "agent.zip")
    modify_webhooks("./workdir/agent/webhooks", "UAT")
    rezip_agent("./workdir/agent/","./workdir/uatagent.zip")
    upload_agent_to_gcs("./workdir/uatagent.zip", bucket_name, "uatagent.zip")
    restore_agent(target_agent_id,  bucket_name,"uatagent.zip", project_id, location)

