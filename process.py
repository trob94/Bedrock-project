#!/usr/bin/env python3
import json
import os
import sys
import boto3

# Get environment from command line
env = sys.argv[1] if len(sys.argv) > 1 else 'beta'

# Connect to AWS services
bedrock = boto3.client('bedrock-runtime', region_name=os.environ['AWS_REGION'])
s3 = boto3.client('s3')

# Get the S3 bucket name
bucket = os.environ[f'S3_BUCKET_{env.upper()}']

print(f"Running {env} deployment to {bucket}")

# Look through all files in prompts folder
for file in os.listdir('prompts'):
    if not file.endswith('.json'):
        continue
    
    print(f"Processing {file}")
    
    # Open and read the prompt config file
    config_file = open(f'prompts/{file}')
    config = json.load(config_file)
    config_file.close()
    
    # Get the template filename
    template_name = config.get('template', file.replace('.json', '.txt'))
    
    # Open and read the template file
    template_file = open(f'templates/{template_name}')
    template = template_file.read()
    template_file.close()
    
    # Get the variables
    variable_sets = config.get('variable_sets', [config.get('variables', {})])
    
    # Process each set of variables
    for i in range(len(variable_sets)):
        vars = variable_sets[i]
        
        # Replace variables in template
        prompt = template
        for key in vars:
            val = vars[key]
            prompt = prompt.replace(f'{{{key}}}', str(val))
        
        # Prepare the request for Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": config.get('max_tokens', 2048),
            "messages": [
                {
                    "role": "user",
                    "content": f"Human: {prompt}"
                }
            ]
        }
        
        # Call Bedrock
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(request_body)
        )
        
        # Read the response
        response_text = response['body'].read()
        response_data = json.loads(response_text)
        content = response_data['content'][0]['text']
        
        # Create filename
        output_name = vars.get('output_name', file.replace('.json', f'_{i}'))
        filename = output_name + '.html'
        
        # Add basic HTML
        html = "<!DOCTYPE html>\n"
        html += "<html>\n"
        html += "<head>\n"
        html += f"<title>{filename}</title>\n"
        html += "<style>body { max-width: 800px; margin: 40px auto; padding: 20px; font-family: Arial; }</style>\n"
        html += "</head>\n"
        html += "<body>\n"
        html += content
        html += "\n</body>\n"
        html += "</html>"
        
        # Upload to S3
        s3_key = f"{env}/outputs/{filename}"
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=html,
            ContentType='text/html'
        )
        
        print(f"Created: {filename}")

print("Done!")
print(f"View at: https://{bucket}.s3-website-{os.environ['AWS_REGION']}.amazonaws.com/")
