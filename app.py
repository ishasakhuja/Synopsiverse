import re
from flask import Flask, render_template, request, redirect, session
import mysql.connector
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)
app.secret_key = 'your_secret_key'
genai.configure(api_key="AIzaSyBBw872-_At2hShtPLSK6D8EptkBcHUCxI")

# Connect to MySQL for login/signup
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="heyy",
    database="Synopsiverse"
)
cursor = db.cursor()

# Function to extract transcript from YouTube
def get_youtube_transcript(video_url):
    # Extract the video ID from the URL
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", video_url)
    if not video_id_match:
        return None, "Invalid YouTube URL."
    
    video_id = video_id_match.group(1)
    
    # Fetch the transcript
    try:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = "\n".join([t['text'] for t in transcript_data])
        return transcript_text, None
    except YouTubeTranscriptApi.CouldNotRetrieveTranscript as e:
        return None, "Could not retrieve transcript. The video may not have a transcript."
    except Exception as e:
        return None, f"An error occurred while fetching the transcript: {str(e)}"

# Function to summarize YouTube transcript
def summarize_youtube_video(video_url):
    # Get the transcript first
    transcript, error = get_youtube_transcript(video_url)
    if error:
        return error  # Return the error message if transcript retrieval failed

    generation_config = {
        "temperature": 0.7,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 2048,
    }
    model = genai.GenerativeModel(model_name="gemini-pro", generation_config=generation_config)

    system_prompt = (
        "System: Create a summary of this YouTube transcript in not more than 3000 words. Make it clear and informative.\n"
    )

    prompt_parts = [system_prompt, transcript]

    response = model.generate_content(prompt_parts)
    return response.text

def is_valid_book_title(book_title):
    generation_config = {
        "temperature": 0.7,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 2048,
    }
    model = genai.GenerativeModel(model_name="gemini-pro", generation_config=generation_config)
    prompt = f"Is the book '{book_title}' available? Answer '1' if the book exists, otherwise '0'."
    response = model.generate_content(prompt)
    if '1' in response.text:
        return True
    elif '0' in response.text:
        return False
    else:
        return True
    
def summarize_book(book_title):
    generation_config = {
        "temperature": 0.7,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 2048,
    }
    model = genai.GenerativeModel(model_name="gemini-pro", generation_config=generation_config)

    system_prompt = "System: User Will Give You A Prompt Of Book Title along with language And You Have To Create a summary in not more than 1000 words. \n"
    prompt_parts = [system_prompt, book_title + "\n"]

    response = model.generate_content(prompt_parts)
    return response.text

def summarize_text(input_text):
    generation_config = {
        "temperature": 0.7,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 2048,
    }
    model = genai.GenerativeModel(model_name="gemini-pro", generation_config=generation_config)

    system_prompt = "System: User Will Give You A Prompt Of Text, Check if the text is summarizable, it should be greater than 1000 words, should gave meaningful words; if not then say that the text is not summarizable, otherwise You Have To Create a line wise summary in 1000 words. \n"
    prompt_parts = [system_prompt, input_text + "\n"]

    response = model.generate_content(prompt_parts)
    return response.text


@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/home')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    else:
        return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None  # Initialize error variable
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if username or email already exists
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        user = cursor.fetchone()
        if user:
            error = "Username or email already exists!"
        else:
            # Insert user into the database
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
            db.commit()
            
            session['username'] = username
            return redirect('/index')  # Redirect to 'index.html' after successful signup
    
    return render_template('signup.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None  # Initialize error variable
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if user exists and password is correct
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        if user:
            session['username'] = username
            return redirect('/index')  # Redirect to the index page after successful login
        else:
            error = "Invalid username or password!"  # Set error message
            
    return render_template('login.html', error=error)  # Pass error message to template

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    content_type = request.form.get('content_type')
    if content_type == 'book':
        book_title = request.form.get('book')
        if not book_title:
            return render_template('error.html', message="Please enter a book title.")
        elif not is_valid_book_title(book_title):
            return render_template('error.html', message="Please enter a valid book title.")
        summary = summarize_book(book_title)
    elif content_type == 'youtube':
        video_url = request.form.get('youtube')
        if not video_url or not re.match(r'^https?:\/\/(?:www\.)?youtube\.com\/.*', video_url):
            return render_template('error.html', message="Please enter a valid YouTube video URL.")
        summary = summarize_youtube_video(video_url)  # Generate summary
    elif content_type == 'text':
        input_text = request.form.get('text')
        if not input_text:
            return render_template('error.html', message="Please enter some text to summarize.")
        summary = summarize_text(input_text)
    else:
        return render_template('error.html', message="Invalid content type.")

    return render_template('summary.html', summary=summary)

@app.route('/history')
def history():
    return render_template('history.html')

if __name__ == '__main__':
    app.run(debug=True)
