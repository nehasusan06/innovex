import gradio as gr

with gr.Blocks(title=" LearnMATE AI") as demo:

    gr.Markdown("""
    # LearnMate AI
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

            process_btn = gr.Button(
                "🚀 Generate Learning Content",
                variant="primary"
            )

        # RIGHT PANEL
        with gr.Column(scale=2):

            chatbot = gr.Chatbot(
                height=100,
                type="messages",
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

        # QUIZ
        with gr.Tab("❓ Quiz"):
            quiz_output = gr.Markdown(
                value="Generated quiz questions will appear here."
            )

        # VIVA
        with gr.Tab("🎤 Viva Questions"):
            viva_output = gr.Markdown(
                value="Generated viva questions will appear here."
            )

        # FLASHCARDS
        with gr.Tab("🃏 Flashcards"):
            flashcard_output = gr.Markdown(
                value="Generated flashcards will appear here."
            )

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

demo.launch()
