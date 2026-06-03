import os
import json
import re
from typing import List
from typing_extensions import TypedDict
import google.generativeai as genai
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("Warning: GEMINI_API_KEY is not set.")

class QuizQuestion(TypedDict):
    question: str
    options: List[str]
    answer_idx: int

class Flashcard(TypedDict):
    front: str
    back: str

class TimestampItem(TypedDict):
    timestamp: str
    topic: str

class VivaQuestion(TypedDict):
    question: str
    answer: str

class LearningBundle(TypedDict):
    summary: str
    notes: str
    quiz: List[QuizQuestion]
    viva: List[VivaQuestion]
    flashcards: List[Flashcard]
    timestamps: List[TimestampItem]

class GenerativeModelWithFallback:
    def __init__(self, default_model_name: str):
        self.default_model_name = default_model_name

    def generate_content(self, prompt: str, generation_config: dict = None) -> any:
        # Prioritized list of models
        models = [
            self.default_model_name,
            "models/gemini-2.5-flash",
            "models/gemini-2.0-flash",
            "models/gemini-flash-latest",
            "models/gemini-2.5-flash-lite"
        ]
        
        # De-duplicate while preserving order
        unique_models = []
        for m in models:
            if m not in unique_models:
                unique_models.append(m)
                
        last_error = None
        for model_name in unique_models:
            try:
                print(f"DEBUG: Trying model '{model_name}'...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                print(f"DEBUG: Model '{model_name}' succeeded!")
                return response
            except Exception as e:
                last_error = e
                print(f"DEBUG: Model '{model_name}' failed: {e}")
                continue
                
        if last_error:
            raise last_error
        raise RuntimeError("No models were available for generation.")

def get_model():
    return GenerativeModelWithFallback("models/gemini-3.5-flash")

def set_api_key(key: str):
    """Dynamically updates the Gemini API key."""
    if key:
        genai.configure(api_key=key.strip())
        os.environ["GEMINI_API_KEY"] = key.strip()

def repair_json_quotes(text: str) -> str:
    """
    Repairs unescaped double quotes inside JSON string values.
    Tracks string states and escapes double quotes that are not followed by JSON delimiters.
    """
    output = []
    in_string = False
    escape_next = False
    i = 0
    n = len(text)
    
    while i < n:
        char = text[i]
        
        if escape_next:
            output.append(char)
            escape_next = False
            i += 1
            continue
            
        if char == '\\':
            output.append(char)
            escape_next = True
            i += 1
            continue
            
        if char == '"':
            if not in_string:
                in_string = True
                output.append(char)
            else:
                j = i + 1
                next_non_ws = None
                while j < n:
                    if not text[j].isspace():
                        next_non_ws = text[j]
                        break
                    j += 1
                
                if next_non_ws in (',', '}', ']', ':'):
                    in_string = False
                    output.append(char)
                else:
                    output.append('\\"')
        else:
            output.append(char)
            
        i += 1
        
    return "".join(output)

def clean_json_string(text: str) -> str:
    """Extracts JSON from markdown code blocks, prefixes, and suffixes, then repairs unescaped quotes."""
    text_stripped = text.strip()
    result = text_stripped
    
    # If it already looks like a JSON object or array
    if (text_stripped.startswith("{") and text_stripped.endswith("}")) or \
       (text_stripped.startswith("[") and text_stripped.endswith("]")):
        result = text_stripped
    else:
        # Try extracting content between ```json and ```
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(pattern, text_stripped)
        matched_clean = False
        if matches:
            for match in matches:
                match_stripped = match.strip()
                if (match_stripped.startswith("{") and match_stripped.endswith("}")) or \
                   (match_stripped.startswith("[") and match_stripped.endswith("]")):
                    result = match_stripped
                    matched_clean = True
                    break
        
        if not matched_clean:
            # Fallback: find the outermost braces/brackets
            first_brace = text_stripped.find('{')
            first_bracket = text_stripped.find('[')
            
            start_idx = -1
            if first_brace != -1 and first_bracket != -1:
                start_idx = min(first_brace, first_bracket)
            elif first_brace != -1:
                start_idx = first_brace
            elif first_bracket != -1:
                start_idx = first_bracket
                
            last_brace = text_stripped.rfind('}')
            last_bracket = text_stripped.rfind(']')
            
            end_idx = -1
            if last_brace != -1 and last_bracket != -1:
                end_idx = max(last_brace, last_bracket)
            elif last_brace != -1:
                end_idx = last_brace
            elif last_bracket != -1:
                end_idx = last_bracket
                
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                candidate = text_stripped[start_idx:end_idx+1]
                candidate_stripped = candidate.strip()
                if (candidate_stripped.startswith("{") and candidate_stripped.endswith("}")) or \
                   (candidate_stripped.startswith("[") and candidate_stripped.endswith("]")):
                    result = candidate_stripped

    # Run the quote repair utility to escape any unescaped inner quotes
    return repair_json_quotes(result)


def generate_summary(transcript: str) -> str:
    """Generates a concise markdown summary of the video transcript."""
    model = get_model()
    prompt = f"""
You are an expert educator. Based on the following YouTube video transcript, generate a structured, professional, and visually engaging summary in Markdown format.
Include:
- 📌 **Core Concept**: 1-2 sentence overview of the video's main idea.
- 🎯 **Target Audience**: Who benefits most from this video.
- 🔑 **Key Takeaways**: Bullet points highlighting the main lessons learned.
- 💡 **Actionable Insights**: How the viewer can apply this knowledge.

Ensure the styling feels premium and clean.

Transcript:
{transcript}
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def generate_notes(transcript: str, difficulty: str, language: str) -> str:
    """Generates detailed study notes based on difficulty and language."""
    model = get_model()
    
    # Adjust explanation style based on difficulty
    difficulty_instructions = {
        "Beginner": "Explain concepts using simple terms, analogies, and step-by-step guides. Avoid overly technical jargon without explaining it first.",
        "Intermediate": "Focus on practical examples, logic, and how concepts fit together. Include code snippets or realistic use cases.",
        "Advanced": "Focus on deep technical details, architectural design, potential edge cases, advanced theories, and optimization strategies."
    }
    
    prompt = f"""
You are an expert lecturer. Based on the video transcript, create detailed and comprehensive study notes in Markdown.
Customize the output based on these criteria:
- **Difficulty Level**: {difficulty} ({difficulty_instructions.get(difficulty, "")})
- **Language**: Translate and write the notes entirely in {language} (if the language is Malayalam or Hindi, write it using that language script naturally, but explain technical terms in English if helpful).

Use rich Markdown elements like bold text, blockquotes for key rules, bullet lists, code blocks (if applicable), and subheadings.

Transcript:
{transcript}
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating notes: {str(e)}"

def generate_quiz(transcript: str) -> list:
    """Generates a JSON list of 5 quiz questions."""
    model = get_model()
    prompt = f"""
Based on the following transcript, generate 5 multiple-choice questions to test comprehension of the content.

You must return the output STRICTLY as a JSON array of objects. Do not include markdown code block tags around the JSON.

JSON Structure:
[
  {{
    "question": "question text",
    "options": ["option 1", "option 2", "option 3", "option 4"],
    "answer_idx": 0
  }}
]

Transcript:
{transcript}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json"
            }
        )
        cleaned_json = clean_json_string(response.text)
        return json.loads(cleaned_json)
    except Exception as e:
        print(f"Error generating quiz JSON: {e}")
        # Fallback empty structure or simple dummy structure
        return [
            {
                "question": "What is the primary topic of the video?",
                "options": ["Not available", "Please check transcript", "Retry generation", "Unknown"],
                "answer_idx": 0
            }
        ]

def generate_viva(transcript: str) -> str:
    """Generates academic viva oral exam questions with collapsible answers."""
    model = get_model()
    prompt = f"""
Based on the transcript, generate 5 viva (oral exam) questions with detailed answers.
Use collapsible HTML `<details>` and `<summary>` tags for each question so that the answer is hidden by default and the user can reveal it.

Example format:
### 🙋 Q1: [Enter question here]
<details>
<summary>Reveal Answer</summary>
[Enter answer here]
</details>

Ensure questions test deep conceptual understanding rather than simple recall.

Transcript:
{transcript}
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating viva questions: {str(e)}"

def generate_flashcards(transcript: str) -> list:
    """Generates a list of 6 flashcard Q&A items."""
    model = get_model()
    prompt = f"""
Based on the transcript, generate 6 high-yield flashcards.

You must return the output STRICTLY as a JSON array of objects. Do not include markdown code block tags around the JSON.

JSON Structure:
[
  {{
    "front": "brief question or key term",
    "back": "brief answer or definition"
  }}
]

Transcript:
{transcript}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json"
            }
        )
        cleaned_json = clean_json_string(response.text)
        return json.loads(cleaned_json)
    except Exception as e:
        print(f"Error generating flashcards JSON: {e}")
        return [
            {"front": "API Error", "back": "Failed to generate flashcards. Please check logs."}
        ]

def generate_timestamps(raw_transcript_entries: list) -> str:
    """Generates a timestamp-based index of key concepts in the video."""
    if not raw_transcript_entries:
        return "Timestamps are not available for this video."
        
    # Build a sampled transcript with timestamps
    sampled_lines = []
    # Sample every ~45 seconds or ~10 entries to keep prompt size reasonable
    step = max(1, len(raw_transcript_entries) // 30)
    for i in range(0, len(raw_transcript_entries), step):
        entry = raw_transcript_entries[i]
        start_seconds = int(entry['start'])
        minutes = start_seconds // 60
        seconds = start_seconds % 60
        timestamp_str = f"[{minutes:02d}:{seconds:02d}]"
        sampled_lines.append(f"{timestamp_str} {entry['text']}")
        
    formatted_transcript_sample = "\n".join(sampled_lines)
    
    model = get_model()
    prompt = f"""
Based on the following timestamped transcript segments, identify 5-7 major milestones or shifts in topics in the video.
For each key topic, provide its exact timestamp in `MM:SS` format (based on the input markers) and a single clear sentence explaining what is covered at that point.

Output format:
- **[MM:SS]** - [Core topic discussed]
- **[MM:SS]** - [Another topic discussed]

Timestamped Transcript Segments:
{formatted_transcript_sample}
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating timestamps: {str(e)}"

def answer_doubt(question: str, transcript: str, chat_history: list) -> tuple[str, list]:
    """
    Answers a question about the video based on the transcript and chat history.
    Returns the answer and the updated chatbot message log.
    """
    model = get_model()
    
    # Format chat history for prompt context
    history_context = ""
    for msg in chat_history:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_context += f"{role}: {msg['content']}\n"
        
    prompt = f"""
You are a helpful learning assistant. Answer the user's question about the video using ONLY the transcript provided as grounding.
If the answer cannot be found in the transcript, politely explain that the video does not cover this topic, but offer a brief general answer if helpful, clearly separating the two.

Video Transcript:
{transcript}

Chat History:
{history_context}

User's Question: {question}

Provide a concise, friendly, and helpful response. Use Markdown.
"""
    try:
        response = model.generate_content(prompt)
        answer = response.text
    except Exception as e:
        answer = f"Error solving doubt: {str(e)}"
        
    # Append the turn to the chat history list
    updated_history = list(chat_history)
    updated_history.append({"role": "user", "content": question})
    updated_history.append({"role": "assistant", "content": answer})
    
    return answer, updated_history

def generate_learning_companion_content(transcript: str, raw_transcript_entries: list, difficulty: str, language: str) -> dict:
    """Generates all study companion components in a single optimized Gemini call."""
    # Build sampled timestamped transcript lines
    sampled_lines = []
    if raw_transcript_entries:
        step = max(1, len(raw_transcript_entries) // 30)
        for i in range(0, len(raw_transcript_entries), step):
            entry = raw_transcript_entries[i]
            start_seconds = int(entry['start'])
            minutes = start_seconds // 60
            seconds = start_seconds % 60
            timestamp_str = f"[{minutes:02d}:{seconds:02d}]"
            sampled_lines.append(f"{timestamp_str} {entry['text']}")
    formatted_transcript_sample = "\n".join(sampled_lines)

    difficulty_instructions = {
        "Beginner": "Explain concepts using simple terms, analogies, and step-by-step guides. Avoid overly technical jargon without explaining it first.",
        "Intermediate": "Focus on practical examples, logic, and how concepts fit together. Include code snippets or realistic use cases.",
        "Advanced": "Focus on deep technical details, architectural design, potential edge cases, advanced theories, and optimization strategies."
    }

    model = get_model()
    prompt = f"""
You are an expert educator. Analyze the provided YouTube video transcript and generate high-yield, concise learning companion content.
Customize the output based on these criteria:
- **Difficulty Level**: {difficulty} ({difficulty_instructions.get(difficulty, "")})
- **Notes Language**: Translate and write the "notes" section entirely in {language}.

To minimize generation time and make the study aids quick to read, make all content highly concise and dense.

You must return the output STRICTLY as a single JSON object with the following keys. Do not include markdown code block tags around the JSON.

JSON Structure:
{{
  "summary": "A brief summary in Markdown (max 150 words). Include a Core Concept overview, target audience, and key takeaways.",
  "notes": "High-yield, concise study notes in Markdown tailored to the {difficulty} difficulty level and written in {language}. Use bullet points, short lists, and minimal code snippets. Avoid wordiness and long paragraphs.",
  "quiz": [
     {{
       "question": "short multiple-choice question testing comprehension",
       "options": ["option 1", "option 2", "option 3", "option 4"],
       "answer_idx": 0
     }}
  ],
  "viva": [
     {{
       "question": "brief conceptual oral exam question",
       "answer": "concise 1-2 sentence answer"
     }}
  ],
  "flashcards": [
     {{
       "front": "brief question or key term",
       "back": "brief answer or definition"
     }}
  ],
  "timestamps": [
     {{
       "timestamp": "MM:SS",
       "topic": "clear sentence explaining the topic discussed at this timestamp based on the markers"
     }}
  ]
}}

Generate exactly 5 items for "quiz", 5 items for "viva", 6 items for "flashcards", and 5-7 items for "timestamps".

Transcript text:
{transcript}

Sampled Timestamped segments:
{formatted_transcript_sample}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json"
            }
        )
        cleaned_json = clean_json_string(response.text)
        data = json.loads(cleaned_json)
        
        # Format timestamps: each on a new line
        raw_timestamps = data.get("timestamps", [])
        formatted_timestamps_list = []
        for item in raw_timestamps:
            ts = item.get("timestamp", "").strip()
            topic = item.get("topic", "").strip()
            formatted_timestamps_list.append(f"- **[{ts}]** - {topic}")
        timestamps_str = "\n".join(formatted_timestamps_list)
        
        # Format viva questions: question and answer in different lines
        raw_viva = data.get("viva", [])
        formatted_viva_list = []
        for idx, item in enumerate(raw_viva):
            q = item.get("question", "").strip()
            a = item.get("answer", "").strip()
            formatted_viva_list.append(f"### 🙋 Q{idx+1}: {q}\n<details>\n<summary>Reveal Answer</summary>\n\n{a}\n</details>")
        viva_str = "\n\n".join(formatted_viva_list)
        
        return {
            "summary": data.get("summary", ""),
            "notes": data.get("notes", ""),
            "quiz": data.get("quiz", []),
            "viva": viva_str,
            "flashcards": data.get("flashcards", []),
            "timestamps": timestamps_str
        }
    except Exception as e:
        print(f"Error in bundle generation: {e}")
        # Return fallback error structures
        return {
            "summary": f"Error generating summary: {str(e)}",
            "notes": f"Error generating notes: {str(e)}",
            "quiz": [],
            "viva": f"Error generating viva questions: {str(e)}",
            "flashcards": [],
            "timestamps": f"Error generating timestamps: {str(e)}"
        }
