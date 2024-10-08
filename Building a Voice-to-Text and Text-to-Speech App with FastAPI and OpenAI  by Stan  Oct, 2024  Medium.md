[

![Stan](https://miro.medium.com/v2/resize:fill:44:44/1*eaB_BJalvqDndgqVxD0PIg.jpeg)



](https://medium.com/@Stan_DS?source=post_page-----630ef5f1e717--------------------------------)

Hong T, Changlu L, Luchao J., Jing W. and Jing Z.

![](https://miro.medium.com/v2/resize:fit:700/1*-McOc9798Z9EewYKzVBEIg.png)

Our web app interactively communicates with ChatGPT APIs. It is powered by OpenAI APIs (Whisper, ChatGPT, TTS), AWS, and Railway.

One of the main motivations behind our project is to bring large language models to a general audience. Allowing users to interact with the system using voice instead of a keyboard offers many advantages. It is more efficient, safer, and appeals to a broader audience, such as seniors or professionals whose work requires constant use of their hands, like factory workers and drivers.

In this blog post, we’ll explore how to build a voice-to-text and text-to-speech system using FastAPI, OpenAI’s Whisper, a text-to-speech engine, and AWS S3 for file storage. We’ll break down the code structure, outline the key steps, highlight the essential tech stacks for setting up the application, and share the insights gained from this project.

## Tech Stack Overview

Before we dive into the code, let’s review the tech stack and its roles in the project:

1\. FastAPI: A modern, fast web framework for building APIs in Python.  
2\. OpenAI Whisper & GPT-4: For transcription (voice-to-text) and language model capabilities (text generation).  
3\. AWS S3: For storing audio files and text files securely in the cloud.  
4\. Docker: To containerize the application, making it easy to deploy and run on any platform.  
5\. Python Libraries:  
— pydantic: For input validation.  
— requests: For making HTTP requests to the FastAPI server.  
— sounddevice, numpy, and scipy: For recording and handling audio locally.  
\- boto3: For interacting with AWS services (like S3).

## Work Steps

**Step 1: FastAPI Setup**

We begin by setting up the FastAPI application. This involves creating a simple API with a /voicebot endpoint that supports both voice and text inputs.

**FastAPI Application**

<pre><code class="">
<span id="9c3a" data-selectable-paragraph=""><br> 
</code></pre>python<br> <span>from</span> fastapi <span>import</span> FastAPI, HTTPException, Form, UploadFile, File<br> <span>from</span> pydantic <span>import</span> BaseModel<br> <span>import</span> os<br> <span>import</span> openai<br> <span>from</span> dotenv <span>import</span> load_dotenv<br> <span>import</span> uuid<br> <span>import</span> boto3<br> <span>from</span> io <span>import</span> BytesIO<br> <br> load_dotenv()<br> app = FastAPI()<br> openai.api_key = os.environ[‘OPENAI_API_KEY’]<br> <br> <br> <span>from</span> fastapi.middleware.cors <span>import</span> CORSMiddleware<br> app.add_middleware(<br> CORSMiddleware,<br> allow_origins=[“*”],<br> allow_credentials=<span>True</span>,<br> allow_methods=[“*”],<br> allow_headers=[“*”],<br> )<br> <br> <br> <span>class</span> <span>QueryInput</span>(<span>BaseModel</span>):<br> input_wav_url: <span>str</span><br> <br> <span>class</span> <span>QueryResponse</span>(<span>BaseModel</span>):<br> output_wav_url: <span>str</span> = <span>None</span><br> return_text: <span>str</span><br> <pre><code class="<br> </span>">

</code></pre>

Here, we configure FastAPI with CORS middleware to allow requests from any origin. We define input and output models (QueryInput and QueryResponse) to ensure clean API responses.

**Step 2: Voicebot Endpoint**

The /api/voicebot/ endpoint processes both text and audio. If the client uploads an audio file, it will first be transcribed using OpenAI’s Whisper model. Otherwise, if text is provided, it goes directly to GPT-4 for processing.

<pre><code class="">
<span id="ff13" data-selectable-paragraph=""> <br> 
</code></pre>python<br><span> @app.post(<span>“/api/voicebot/”, response_model=QueryResponse</span>)</span><br> <span>async</span> <span>def</span> <span>voicebot_endpoint</span>(<span><br> audio: UploadFile = File(<span><span>None</span></span>), <br> text: <span>str</span> = Form(<span><span>None</span></span>) <br> </span>):<br> <br> s3 = boto3.client(‘s3’)<br> bucket_name = ‘voicebot-text-to-speech’<br> <br> <span>if</span> audio:<br> <br> content = <span>await</span> audio.read()<br> file_extension = os.path.splitext(audio.filename)[<span>1</span>]<br> file_name = f”input_{uuid.uuid4()}{file_extension}”<br> <br> <br> file_buffer = BytesIO(content)<br> s3.upload_fileobj(file_buffer, bucket_name, file_name)<br> <br> <br> transcript = openai.Audio.transcribe(<br> model=”whisper-<span>1</span><span>",<br> file=(audio.filename, content),<br> response_format=”text”<br> )<br> elif text:<br> transcript = text<br> else:<br> raise HTTPException(status_code=400, detail=”Audio or text input required”)<br> <br> # Send transcript to GPT-4<br> response = openai.Completion.create(<br> model=”gpt-4–1106-preview”,<br> messages=[<br> {“role”: “system”, “content”: “You are a helpful assistant.”},<br> {“role”: “user”, “content”: transcript}<br> ]<br> )<br> <br> # Convert GPT-4 response to speech<br> gpt_response = response.choices[0].message.content<br> speech_response = openai.Audio.create_speech(<br> model=”tts-1"</span>,<br> voice=”nova”,<br> <span>input</span>=gpt_response<br> )<br> <br> <br> speech_file = BytesIO()<br> <span>for</span> chunk <span>in</span> speech_response.iter_bytes(chunk_size=<span>4096</span>):<br> speech_file.write(chunk)<br> speech_file.seek(<span>0</span>)<br> speech_file_name = f”speech_{uuid.uuid4()}.mp3<span>"<br> s3.upload_fileobj(speech_file, bucket_name, speech_file_name)<br> <br> # Generate URL to access speech file<br> url = s3.generate_presigned_url(‘get_object’, Params={‘Bucket’: bucket_name, ‘Key’: speech_file_name}, ExpiresIn=3600)<br> <br> return QueryResponse(output_wav_url=url, return_text=gpt_response)<br> <pre><code class="<br> </span></span>">

</code></pre>

**Step 3: Dockerizing the Application**

Containerizing the application with Docker ensures that the API can run anywhere, from your local machine to a cloud platform like AWS or Railway.

<pre><code class="">
<span id="34b1" data-selectable-paragraph=""><br> Dockerfile<br> <br> 
</code></pre>dockerfile<br> <span>FROM</span> python:<span>3.9</span><span>.6</span><br> <br> WORKDIR <span>/</span>code<br> <br> <span>COPY</span> requirements.txt .<br> RUN pip install — <span>no</span><span>-</span>cache<span>-</span>dir — upgrade <span>-</span>r requirements.txt<br> <br> <span>COPY</span> .<span>/</span>app<span>/</span> .<span>/</span>app<br> <br> EXPOSE <span>8000</span><br> <br> RUN useradd <span>-</span>m appuser<br> <span>USER</span> appuser<br> <br> CMD [“uvicorn”, “app.main:app”, “ — host”, “<span>0.0</span><span>.0</span><span>.0</span>”, “ — port”, “<span>8000</span>”]<br> <pre><code class="</span>">

</code></pre>

This Dockerfile sets up the Python environment, installs dependencies, and uses uvicorn to serve the FastAPI application.

**Step 4: Recording and Sending Audio**

We also implement a Python client to record audio and send it to the API. This allows us to test the voicebot locally.

Client-Side Audio Recording

<pre><code class="">
<span id="7742" data-selectable-paragraph=""><br> 
</code></pre>python<br> <span>import</span> sounddevice <span>as</span> sd<br> <span>from</span> scipy.io.wavfile <span>import</span> write<br> <span>import</span> requests<br> <span>import</span> numpy <span>as</span> np<br> <br> <br> fs = <span>44100</span> <br> duration = <span>5</span> <br> <br> <span>print</span>(“Recording…”)<br> myrecording = sd.rec(<span>int</span>(duration * fs), samplerate=fs, channels=<span>1</span>)<br> sd.wait()<br> <br> <br> audio_file = ‘./data/audio_input.wav’<br> write(audio_file, fs, np.int16(myrecording * <span>32767</span>))<br> <br> <br> <span>def</span> <span>send_audio</span>(<span>file_path</span>):<br> <span>with</span> <span>open</span>(file_path, ‘rb’) <span>as</span> f:<br> files = {‘audio’: (file_path, f, ‘audio/wav’)}<br> response = requests.post(“http://localhost:<span>8000</span>/api/voicebot/”, files=files)<br> <span>return</span> response<br> <br> response = send_audio(audio_file)<br> <span>print</span>(response.json())<br> <pre><code class="<br> </span>">

</code></pre>

**Step 5: Deploying to the Cloud**

Once the application is tested locally, you can deploy it to services like AWS EC2, Railway, or any other container-based cloud provider.

AWS ECS: Launch an EC2 instance, SSH into it, install Docker, and run the FastAPI container.  
Railway: Push your code to Railway, which automatically builds and deploys the app.

**Challenges and Lessons learned:**

**It is easy to develop a proof of concept (POC) using a notebook, but building a running web app is much more challenging.** In addition to learning how to write backend APIs and set up databases, we encountered many issues with building the frontend app. One of the main challenges was ensuring seamless communication between the backend and frontend without significant latency. Initially, we tried limiting GPT responses, but eventually, storing audio files in the browser cache and directly triggering the endpoint allowed us to provide a good user experience with minimal lag between voice recording and responses.

**Cost**: We initially deployed the API on AWS ECS, which made it straightforward to set up clusters and control HTTP inbound and outbound traffic. However, this convenience came with a high cost. With minimal traffic, our cluster generated a $10 bill over a single weekend, which we knew wasn’t sustainable. We then switched to Railway.app, signing up for their hobbyist membership. With a $5 monthly fee, we were able to deploy and host the web app successfully without worrying about excessive costs.

**CI/CD**: During development, we built and tested the API locally, then deployed the code to a Docker container for further testing. Eventually, we deployed the Docker image on Railway.app. Manual code updates quickly became unsustainable, so we connected Railway to our GitHub repository. Now, it automatically updates the FastAPI online whenever we push new code updates, enabling continuous deployment. The process is quite impressive.

**Conclusion**

In this tutorial, we’ve demonstrated how to build a voice bot that handles voice-to-text and text-to-speech using FastAPI, OpenAI models, and AWS S3 for storage. We also containerized the app with Docker for easy deployment. The next step is to expand the app to address specific customer issues. The app serves as a vehicle to bring our research in Retrieval-Augmented Generation (RAG), model training, and evaluation to the end user. The possibilities are endless!

There is no doubt there will be challenges and road blocks, but if we’ve come this far, we might as well keep going.  
**Happy coding!**

The authors thank OpenAI Research Funding for providing testing tokens for this project.
