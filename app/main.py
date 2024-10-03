# %%
from fastapi import FastAPI, HTTPException, Body, Form, UploadFile, File
from typing import Optional
from pydantic import BaseModel, Field
from pydantic import ValidationError
from typing import Dict, Any
from typing import List, Optional, Tuple
from fastapi.middleware.cors import CORSMiddleware
import os
import openai
from openai import OpenAI
from getpass import getpass
from dotenv import load_dotenv
load_dotenv()
import uuid


import boto3
from io import BytesIO

OpenAI.api_key = os.environ['OPENAI_API_KEY']
app = FastAPI()

# %%
# Set up CORS middleware options.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
# %%
# %%
class QueryInput(BaseModel): #.wav url
    input_wav_url: str
class QueryResponse(BaseModel):
    output_wav_url: Optional[str]
    return_text: str
#
@app.post("/api/voicebot/", response_model=QueryResponse)
async def voicebot_endpoint(
    audio: UploadFile = File(None),
    text: str = Form(None)
):
    
    if audio:
        print(f'Audio file received: {audio.filename}')

        # Read the content of the uploaded file
        content = await audio.read()

        # Prepare the file as a tuple (filename, content)
        audio_data = (audio.filename, content)

        # Upload the audio file to S3

        s3 = boto3.client('s3')
        bucket_name = 'voicebot-text-to-speech'  # Replace with your actual S3 bucket name
        file_extension = os.path.splitext(audio.filename)[1]
        file_name = f"input_{uuid.uuid4()}{file_extension}"
        
        # Save the file in its original format
        try:
            # Create a BytesIO object from the content
            file_buffer = BytesIO(content)
            file_buffer.seek(0)

            # Upload the file to S3 in its original format
            s3.upload_fileobj(file_buffer, bucket_name, file_name)
        except Exception as e:
            print(f"Error uploading file to S3: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error uploading file to S3: {str(e)}")
        
        print(f"Audio file uploaded to S3 in original format: {file_name}")


        # 使用 Whisper 将语音转换为文本
        client = OpenAI()
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_data,
            response_format="text"
        )
    elif text:
        # 如果没有音频文件,使用提供的文本
        transcript = text
    else:
        raise HTTPException(status_code=400, detail="需要提供音频文件或文本")
    print(f'transcript is {transcript}')
    # 发送转录文本到 GPT-4 模型获取回答

    sys_msg = """ 
You are a helpful bilingual tutor who is helping a 7-10 years old student learning a new language. 
Strictly take the following steps before you answer the student's question:

1- Identify the native language of the student.
2- Identify the intent of the student's question:
    - Are they asking to practice the language they are learning through conversation?
    - Are they asking for help to learn the langugage?
3- Generate output based on the identified intent of the student's question.
    - If the student is asking for help to learn the language, output your answer in their native language.
    - If the student is asking to practice the language they are learning through conversation, output your answer in the language they are learning.

Your tone should be friendly and encouraging.

Now continue the conversation with the student, and strictly only output the answer to the student's question without explaining the thought process of the above steps.

following are few examples of the conversation history:
student: 你能教我怎么用spanish说吗
tutor: 当然可以，你想学什么？
student: 基本的日常对话
tutor: 当然可以，你想学什么？
student:西班牙语中，你好怎么说？
tutor: 你好，在西班牙语中，你好是“Hola”。
student:西班牙语中，再见怎么说？
tutor: 再见，在西班牙语中，再见是“Adiós”。
student:西班牙语中，对不起怎么说？
tutor: 对不起，在西班牙语中，对不起是“Perdón”。
student:西班牙语中，谢谢怎么说？
tutor: 谢谢，在西班牙语中，谢谢是“Gracias”。
student:西班牙语中，你好吗？怎么说？
tutor: 你好吗？在西班牙语中，你好吗？是“¿Cómo estás？”。
student:西班牙语中，你叫什么名字？怎么说？
tutor: 你叫什么名字？在西班牙语中，你叫什么名字？是“¿Cómo te llamas？”。
"""

    # Initialize conversation history if it doesn't exist
    if not hasattr(app, 'conversation_history'):
        app.conversation_history = []

    # Function to update conversation history
    def update_conversation_history(user_input, model_response):
        app.conversation_history.append({"role": "user", "content": user_input})
        app.conversation_history.append({"role": "assistant", "content": model_response})

    # Function to get conversation messages
    def get_conversation_messages():
        system_message = {"role": "system", "content": sys_msg}
        return [system_message] + app.conversation_history[-6:]

    # Prepare messages for the API call
    messages = get_conversation_messages()
    messages.append({"role": "user", "content": transcript})

    completion = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=messages
    )
    response = completion.choices[0].message.content
    print(f'response is {response}')

    # Update conversation history
    update_conversation_history(transcript, response)
    # 返回 QueryResponse
    # Generate speech from the response text
    speech_file = BytesIO()
    speech_response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=response
    )
    
    # Save the audio content to the BytesIO object
    for chunk in speech_response.iter_bytes(chunk_size=4096):
        speech_file.write(chunk)
    
    # Reset the file pointer to the beginning
    speech_file.seek(0)
    
    # Upload the audio file to S3
    s3 = boto3.client('s3')
    bucket_name = 'voicebot-text-to-speech'  # Replace with your actual S3 bucket name
    file_name = f"speech_{uuid.uuid4()}.mp3"
    
    s3.upload_fileobj(speech_file, bucket_name, file_name)
    
    # Generate a presigned URL for the uploaded file
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': file_name},
        ExpiresIn=3600  # URL expires in 1 hour
    )
    print(f'url is {url}')
    return QueryResponse(output_wav_url=url, return_text=response)