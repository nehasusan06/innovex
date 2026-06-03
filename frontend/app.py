import os
import gradio as gr
from dotenv import load_dotenv

# Import services
import youtube_service
import gemini_service

# Load environmental variables
load_dotenv()

# Session state store for reliable cross-callback data sharing
session_data = {
    "transcript": "",
    "title": ""
}

# Set up custom premium CSS
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

body, .gradio-container {
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.title-container {
    text-align: center;
    margin-bottom: 25px !important;
    padding: 15px 0;
}

.title-container h1 {
    background: linear-gradient(135deg, #FF3366 0%, #7000FF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800 !important;
    font-size: 2.8rem !important;
    margin: 0 !important;
    line-height: 1.2;
}

.title-container h3 {
    color: #64748B;
    font-weight: 500 !important;
    font-size: 1.2rem !important;
    margin: 8px 0 0 0 !important;
}

/* Button enhancements */
button.primary, .primary-btn {
    background: linear-gradient(135deg, #7000FF 0%, #4D00B4 100%) !important;
    border: none !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 12px rgba(112, 0, 255, 0.2) !important;
}

button.primary:hover, .primary-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 18px rgba(112, 0, 255, 0.35) !important;
}

/* Dashboard block aesthetics */
.stat-block {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    transition: all 0.3s ease;
}

/* Light Mode */
.stat-block {
    color: #1E293B;
}

/* Dark mode compatibility override */
.dark .stat-block {
    background: #1E293B !important;
    border-color: #334155 !important;
}

.dark .stat-block, .dark .stat-block * {
    color: #F1F5F9 !important;
}
"""

def get_card_markup(cards: list, index: int, side: str) -> tuple[str, str]:
    """Generates the HTML representation of a flashcard."""
    if not cards or index >= len(cards):
        return """
        <div style="background: #F1F5F9; padding: 40px; border-radius: 12px; text-align: center; color: #64748B; border: 1px solid #E2E8F0; min-height: 180px; display: flex; justify-content: center; align-items: center;">
            <h3 style="margin:0;">No Flashcards Loaded</h3>
        </div>
        """, "Card 0 of 0"
        
    card = cards[index]
    content = card["back"] if side == "back" else card["front"]
    side_label = "BACK (Explanation)" if side == "back" else "FRONT (Concept/Question)"
    bg_gradient = "linear-gradient(135deg, #1E1B4B 0%, #312E81 100%)" if side == "back" else "linear-gradient(135deg, #0F172A 0%, #1E293B 100%)"
    border_color = "#4338CA" if side == "back" else "#334155"
    text_color = "#E0E7FF" if side == "back" else "#F8FAFC"
    label_color = "#818CF8" if side == "back" else "#94A3B8"
    
    html = f"""
    <div style="background: {bg_gradient}; padding: 40px; border-radius: 12px; text-align: center; color: white; border: 2px solid {border_color}; min-height: 200px; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3); margin-bottom: 20px; transition: all 0.3s ease;">
        <span style="font-size: 12px; text-transform: uppercase; letter-spacing: 2px; color: {label_color}; margin-bottom: 15px; font-weight: 700;">{side_label}</span>
        <h2 style="margin: 0; font-size: 20px; line-height: 1.5; color: {text_color}; font-weight: 600;">{content}</h2>
    </div>
    """
    counter = f"Card {index + 1} of {len(cards)}"
    return html, counter

def process_video(url, diff, lang, watched_val, history_val, completed_val):
    """Callback when 'Generate Learning Content' is clicked."""
    # Create the default dictionary with all components set to no-op update
    response = {
        summary_output: gr.update(),
        notes_output: gr.update(),
        viva_output: gr.update(),
        timestamp_output: gr.update(),
        transcript_state: gr.update(),
        current_video_title: gr.update(),
        quiz_state: gr.update(),
        flashcards_state: gr.update(),
        current_card_idx: gr.update(),
        current_card_side: gr.update(),
        current_video_completed: gr.update(),
        quiz_welcome: gr.update(),
        quiz_submit_btn: gr.update(),
        quiz_score_output: gr.update(),
        flashcard_welcome: gr.update(),
        flashcard_area: gr.update(),
        flashcard_content: gr.update(),
        card_counter: gr.update(),
        videos_watched: gr.update(),
        learning_history: gr.update(),
        progress: gr.update(),
        videos_watched_val: gr.update(),
        learning_history_val: gr.update()
    }
    for i in range(5):
        response[quiz_blocks[i]] = gr.update()
        response[quiz_questions_components[i]] = gr.update()
        response[quiz_options_components[i]] = gr.update()
        response[quiz_feedback_components[i]] = gr.update()

    # Handle key validation
    if not os.getenv("GEMINI_API_KEY"):
        err_msg = "⚠️ Gemini API Key is missing. Please set it in .env."
        response[summary_output] = err_msg
        response[notes_output] = err_msg
        response[viva_output] = err_msg
        response[timestamp_output] = err_msg
        return response

    video_id = youtube_service.extract_video_id(url)
    if not video_id:
        err_msg = "⚠️ Invalid YouTube URL. Please verify the link format."
        response[summary_output] = err_msg
        response[notes_output] = err_msg
        response[viva_output] = err_msg
        response[timestamp_output] = err_msg
        return response

    # Fetch Video Title using oEmbed API
    video_title = youtube_service.get_video_title(video_id)

    # Fetch Video Transcript
    transcript_text, raw_transcript = youtube_service.get_transcript(video_id)
    if transcript_text.startswith("Error"):
        err_msg = f"⚠️ {transcript_text}"
        response[summary_output] = err_msg
        response[notes_output] = err_msg
        response[viva_output] = err_msg
        response[timestamp_output] = err_msg
        return response

    # Store in session state for reliable cross-callback access
    session_data["transcript"] = transcript_text
    session_data["title"] = video_title

    # Generate content using Gemini in a single bundled API request (highly optimized)
    bundle = gemini_service.generate_learning_companion_content(transcript_text, raw_transcript, diff, lang)
    
    summary = bundle.get("summary", "Error generating summary.")
    notes = bundle.get("notes", "Error generating notes.")
    quiz = bundle.get("quiz", [])
    viva = bundle.get("viva", "Error generating viva questions.")
    flashcards = bundle.get("flashcards", [])
    timestamps = bundle.get("timestamps", "Error generating timestamps.")

    # Initialize flashcard side markup
    initial_card_html, counter_text = get_card_markup(flashcards, 0, "front")

    # Update dashboard records
    already_exists = False
    new_history = list(history_val)
    for idx, item in enumerate(new_history):
        if item[0] == video_title:
            already_exists = True
            # Reset existing entry for a re-take
            new_history[idx] = [video_title, "In Progress", "N/A"]
            break
            
    new_watched = watched_val
    if not already_exists:
        new_watched += 1
        new_history.append([video_title, "In Progress", "N/A"])
        
    current_progress = (completed_val / max(1, new_watched)) * 100

    # Build response updates
    response.update({
        summary_output: summary,
        notes_output: notes,
        viva_output: viva,
        timestamp_output: timestamps,
        transcript_state: transcript_text,
        current_video_title: video_title,
        quiz_state: quiz,
        flashcards_state: flashcards,
        current_card_idx: 0,
        current_card_side: "front",
        current_video_completed: False,
        
        # Quiz visibility
        quiz_welcome: gr.update(visible=False),
        quiz_submit_btn: gr.update(visible=True),
        quiz_score_output: gr.update(visible=True, value=""),
        
        # Flashcards visibility
        flashcard_welcome: gr.update(visible=False),
        flashcard_area: gr.update(visible=True),
        flashcard_content: initial_card_html,
        card_counter: counter_text,
        
        # Dashboard updates
        videos_watched: new_watched,
        learning_history: new_history,
        progress: current_progress,
        videos_watched_val: new_watched,
        learning_history_val: new_history
    })

    # Map the 5 quiz questions to Radio options
    for i in range(5):
        if i < len(quiz):
            q = quiz[i]
            response[quiz_blocks[i]] = gr.update(visible=True)
            response[quiz_questions_components[i]] = f'''
<div style="background:#4C1D95;padding:15px;border-radius:10px;font-size:20px;font-weight:700;color:#FFFFFF;border:1px solid #7C3AED;">
🙋 Question {i+1}: {q['question']}
</div>
'''
            response[quiz_options_components[i]] = gr.update(choices=q['options'], value=None)
            response[quiz_feedback_components[i]] = ""
        else:
            response[quiz_blocks[i]] = gr.update(visible=False)
            response[quiz_questions_components[i]] = gr.update(visible=False)
            response[quiz_options_components[i]] = gr.update(visible=False)
            response[quiz_feedback_components[i]] = gr.update(visible=False)

    print(f"DEBUG: process_video completed. title={video_title[:30].encode('ascii', errors='replace').decode()} transcript_len={len(transcript_text)}")
    return response

def submit_quiz(q1, q2, q3, q4, q5, quiz_data, video_title, watched_val, completed_val, history_val, scores_list, already_completed):
    """Callback when Quiz is submitted."""
    response = {
        quiz_score_output: gr.update(),
        completed_topics: gr.update(),
        average_quiz_score: gr.update(),
        progress: gr.update(),
        learning_history: gr.update(),
        completed_topics_val: gr.update(),
        quiz_scores_list: gr.update(),
        learning_history_val: gr.update(),
        current_video_completed: gr.update()
    }
    for i in range(5):
        response[quiz_feedback_components[i]] = gr.update()

    if not quiz_data:
        response[quiz_score_output] = "⚠️ No active quiz data."
        return response
        
    user_answers = [q1, q2, q3, q4, q5]
    correct_count = 0
    
    # Evaluate answers
    for i in range(5):
        if i < len(quiz_data):
            q = quiz_data[i]
            user_ans = user_answers[i]
            correct_idx = q['answer_idx']
            correct_ans_text = q['options'][correct_idx]
            
            if user_ans == correct_ans_text:
                correct_count += 1
                feedback_str = "✅ **Correct!**"
            else:
                feedback_str = f"❌ **Incorrect.** Correct answer is: **{correct_ans_text}**"
                
            response[quiz_feedback_components[i]] = feedback_str
        else:
            response[quiz_feedback_components[i]] = ""
            
    score_percent = int((correct_count / len(quiz_data)) * 100)
    
    # Custom HTML styling for Score Box
    score_markdown = f"""
    <div style="background: rgba(112, 0, 255, 0.08); border: 2px solid #7000FF; border-radius: 12px; padding: 25px; text-align: center; margin-top: 20px; box-shadow: 0 4px 12px rgba(112, 0, 255, 0.1);">
        <h2 style="margin: 0 0 10px 0; color: #7000FF; font-weight: 700; font-family: 'Outfit';">🏆 Quiz Results</h2>
        <p style="font-size: 32px; font-weight: 800; margin: 10px 0; color: #1E293B;">{correct_count} / {len(quiz_data)} ({score_percent}%)</p>
        <p style="color: #64748B; margin: 0; font-weight: 500;">Progress Dashboard updated successfully.</p>
    </div>
    """
    response[quiz_score_output] = score_markdown
    
    # Update dashboard scores list and history
    new_completed = completed_val
    new_scores = list(scores_list)
    new_history = list(history_val)
    
    for idx, item in enumerate(new_history):
        if item[0] == video_title:
            new_history[idx] = [video_title, "Completed", f"{score_percent}%"]
            break
            
    if not already_completed:
        new_completed += 1
        new_scores.append(score_percent)
    else:
        # Update last score if they retake
        if new_scores:
            new_scores[-1] = score_percent
        else:
            new_scores.append(score_percent)
            
    avg_score = int(sum(new_scores) / len(new_scores)) if new_scores else 0
    current_progress = (new_completed / max(1, watched_val)) * 100
    
    response.update({
        completed_topics: new_completed,
        average_quiz_score: avg_score,
        progress: current_progress,
        learning_history: new_history,
        
        # State variables
        completed_topics_val: new_completed,
        quiz_scores_list: new_scores,
        learning_history_val: new_history,
        current_video_completed: True
    })
    
    return response

# Flashcard Actions
def flip_card_action(cards, index, side):
    new_side = "back" if side == "front" else "front"
    html, counter = get_card_markup(cards, index, new_side)
    return html, new_side

def next_card_action(cards, index):
    if not cards:
        return "", 0, "front", "Card 0 of 0"
    new_index = (index + 1) % len(cards)
    html, counter = get_card_markup(cards, new_index, "front")
    return html, new_index, "front", counter

def prev_card_action(cards, index):
    if not cards:
        return "", 0, "front", "Card 0 of 0"
    new_index = (index - 1) % len(cards)
    html, counter = get_card_markup(cards, new_index, "front")
    return html, new_index, "front", counter

# Chatbot Doubt Solver Action
def chat_interaction(user_msg, chat_history, transcript_text):
    transcript_text = session_data["transcript"]
    print(f"DEBUG: chat_interaction called - user_msg={repr(user_msg)}, transcript_len={len(transcript_text)}")
    if not user_msg.strip():
        return "", chat_history
        
    if not transcript_text:
        updated_history = list(chat_history)
        updated_history.append({"role": "user", "content": user_msg})
        updated_history.append({"role": "assistant", "content": "⚠️ Please paste a YouTube URL and click 'Generate Learning Content' first so I have context to answer your questions!"})
        return "", updated_history
        
    answer, updated_history = gemini_service.answer_doubt(user_msg, transcript_text, chat_history)
    return "", updated_history


with gr.Blocks(title="learnMate AI") as demo:
    # State management variables
    transcript_state = gr.State("")
    current_video_title = gr.State("")
    quiz_state = gr.State([])
    flashcards_state = gr.State([])
    current_card_idx = gr.State(0)
    current_card_side = gr.State("front")
    
    # Progress dashboard states
    videos_watched_val = gr.State(0)
    completed_topics_val = gr.State(0)
    quiz_scores_list = gr.State([])
    learning_history_val = gr.State([])
    current_video_completed = gr.State(False)

    with gr.Column(elem_classes=["title-container"]):
        gr.Markdown("""
        # 🚀 learnMate AI
        ### AI-Powered YouTube Learning
        """)

    with gr.Row():

        # LEFT PANEL
        with gr.Column(scale=1):
            youtube_url = gr.Textbox(
                label="🎥 YouTube Video URL",
                placeholder="Paste YouTube link here..."
            )

            difficulty = gr.Dropdown(
                ["Beginner", "Intermediate", "Advanced"],
                value="Beginner",
                label="Difficulty Level"
            )

            language = gr.Dropdown(
                ["English", "Malayalam", "Hindi"],
                value="English",
                label="Notes Language"
            )
            
            # API key override removed, reads from .env directly

            process_btn = gr.Button(
                "🚀 Generate Learning Content",
                variant="primary"
            )

        # RIGHT PANEL
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                height=350,
                label="💬 AI Doubt Solver"
            )

            with gr.Row():
                question = gr.Textbox(
                    placeholder="Ask a question about the video...",
                    show_label=False,
                    scale=8
                )

                send_btn = gr.Button(
                    "📤 Send",
                    variant="primary",
                    scale=1
                )

    # TABS
    with gr.Tabs():

        # SUMMARY
        with gr.Tab("📄 Summary"):
            summary_output = gr.Markdown(
                value="Generated summary will appear here."
            )

        # NOTES
        with gr.Tab("📝 Notes"):
            notes_output = gr.Markdown(
                value="Generated notes will appear here."
            )

        # QUIZ (Interactive Mode!)
        with gr.Tab("❓ Quiz"):
            quiz_welcome = gr.Markdown(
                value="Generated quiz questions will appear here."
            )
            
            # Interactive Quiz Components
            quiz_blocks = []
            quiz_questions_components = []
            quiz_options_components = []
            quiz_feedback_components = []
            
            for i in range(5):
                with gr.Column(visible=False, elem_classes=["stat-block"]) as q_col:
                    q_text = gr.HTML("")
                    q_opt = gr.Radio(choices=[], label="Select the best answer:")
                    q_feed = gr.Markdown("")
                    
                    quiz_blocks.append(q_col)
                    quiz_questions_components.append(q_text)
                    quiz_options_components.append(q_opt)
                    quiz_feedback_components.append(q_feed)
            
            quiz_submit_btn = gr.Button("Submit Answers", variant="primary", visible=False)
            quiz_score_output = gr.Markdown("", visible=False)

        # VIVA
        with gr.Tab("🎤 Viva Questions"):
            viva_output = gr.Markdown(
                value="Generated viva questions will appear here."
            )

        # FLASHCARDS (Interactive Flippable Mode!)
        with gr.Tab("🃏 Flashcards"):
            flashcard_welcome = gr.Markdown(
                value="Generated flashcards will appear here."
            )
            
            with gr.Column(visible=False) as flashcard_area:
                flashcard_content = gr.HTML("")
                with gr.Row():
                    prev_card_btn = gr.Button("⬅️ Previous", scale=1)
                    flip_card_btn = gr.Button("🔄 Flip Card", variant="primary", scale=2)
                    next_card_btn = gr.Button("Next ➡️", scale=1)
                card_counter = gr.Markdown("Card 1 of 6", elem_classes=["text-center"])

        # TIMESTAMPS
        with gr.Tab("⏱ Important Timestamps"):
            timestamp_output = gr.Markdown(
                value="Important timestamps will appear here."
            )

        # PROGRESS DASHBOARD
        with gr.Tab("📊 Progress Dashboard"):
            with gr.Row():
                completed_topics = gr.Number(
                    label="📚 Completed Topics",
                    value=0,
                    interactive=False
                )

                videos_watched = gr.Number(
                    label="🎥 Videos Watched",
                    value=0,
                    interactive=False
                )

                average_quiz_score = gr.Number(
                    label="🏆 Average Quiz Score (%)",
                    value=0,
                    interactive=False
                )

            progress = gr.Slider(
                minimum=0,
                maximum=100,
                value=0,
                label="Overall Learning Progress",
                interactive=False
            )

            learning_history = gr.Dataframe(
                headers=["Video", "Status", "Quiz Score"],
                label="Learning History",
                interactive=False
            )

    # Wire up the Event Handlers
    
    # 1. Process Video Action
    process_btn.click(
        fn=process_video,
        inputs=[
            youtube_url, 
            difficulty, 
            language, 
            videos_watched_val,
            learning_history_val,
            completed_topics_val
        ],
        outputs=[
            summary_output,
            notes_output,
            viva_output,
            timestamp_output,
            transcript_state,
            current_video_title,
            quiz_state,
            flashcards_state,
            current_card_idx,
            current_card_side,
            current_video_completed,
            quiz_welcome,
            quiz_submit_btn,
            quiz_score_output,
            flashcard_welcome,
            flashcard_area,
            flashcard_content,
            card_counter,
            videos_watched,
            learning_history,
            progress,
            videos_watched_val,
            learning_history_val,
            *quiz_blocks,
            *quiz_questions_components,
            *quiz_options_components,
            *quiz_feedback_components
        ]
    )

    # 2. Quiz Submission Action
    quiz_submit_btn.click(
        fn=submit_quiz,
        inputs=[
            *quiz_options_components,
            quiz_state,
            current_video_title,
            videos_watched_val,
            completed_topics_val,
            learning_history_val,
            quiz_scores_list,
            current_video_completed
        ],
        outputs=[
            quiz_score_output,
            completed_topics,
            average_quiz_score,
            progress,
            learning_history,
            completed_topics_val,
            quiz_scores_list,
            learning_history_val,
            current_video_completed,
            *quiz_feedback_components
        ]
    )

    # 3. Flashcard Controls Actions
    flip_card_btn.click(
        fn=flip_card_action,
        inputs=[flashcards_state, current_card_idx, current_card_side],
        outputs=[flashcard_content, current_card_side]
    )
    
    next_card_btn.click(
        fn=next_card_action,
        inputs=[flashcards_state, current_card_idx],
        outputs=[flashcard_content, current_card_idx, current_card_side, card_counter]
    )
    
    prev_card_btn.click(
        fn=prev_card_action,
        inputs=[flashcards_state, current_card_idx],
        outputs=[flashcard_content, current_card_idx, current_card_side, card_counter]
    )

    # 4. Doubt Solver Actions
    send_btn.click(
        fn=chat_interaction,
        inputs=[question, chatbot, transcript_state],
        outputs=[question, chatbot]
    )
    
    question.submit(
        fn=chat_interaction,
        inputs=[question, chatbot, transcript_state],
        outputs=[question, chatbot]
    )

if __name__ == "__main__":
    demo.launch(css=custom_css)
