document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("quiz-form");
    if (!form) return;

    const cards = Array.from(form.querySelectorAll(".question-card"));
    const nextButton = document.getElementById("quiz-next-button");
    const actionNote = document.getElementById("quiz-action-note");
    const progressElements = [
        document.getElementById("quiz-progress"),
        document.getElementById("quiz-progress-bottom"),
    ].filter(Boolean);
    const progressFill = document.getElementById("quiz-progress-fill");
    let currentIndex = 0;
    let answerIsVisible = false;

    function currentCard() {
        return cards[currentIndex];
    }

    function updateProgress() {
        const text = `Câu ${currentIndex + 1}/${cards.length}`;
        progressElements.forEach((element) => {
            element.textContent = text;
        });
        if (progressFill) {
            progressFill.style.width = `${cards.length ? ((currentIndex + 1) / cards.length) * 100 : 0}%`;
        }
    }

    function showCurrentCard() {
        cards.forEach((card, index) => {
            card.hidden = index !== currentIndex;
        });
        answerIsVisible = false;
        nextButton.type = "button";
        nextButton.textContent = "Next - Xem đáp án →";
        actionNote.textContent = "Chọn đáp án, sau đó bấm Next để xem đáp án đúng.";
        updateProgress();
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function revealAnswer() {
        const card = currentCard();
        const options = Array.from(card.querySelectorAll(".quiz-option"));
        const selectedOptions = options.filter((option) => option.querySelector("input").checked);
        const correctOptions = options.filter((option) => option.dataset.correct === "true");
        const selectedCorrectly =
            selectedOptions.length === correctOptions.length &&
            selectedOptions.every((option) => option.dataset.correct === "true");

        options.forEach((option) => {
            const input = option.querySelector("input");
            input.disabled = true;
            if (option.dataset.correct === "true") {
                option.classList.add("revealed-correct");
            } else if (input.checked) {
                option.classList.add("revealed-wrong");
            }
        });

        const feedback = card.querySelector(".answer-feedback");
        feedback.classList.add("is-visible");
        if (selectedOptions.length === 0) {
            feedback.classList.add("feedback-unanswered");
            feedback.textContent = "Bạn chưa chọn đáp án. Đáp án đúng đã được hiển thị.";
        } else if (selectedCorrectly) {
            feedback.classList.add("feedback-correct");
            feedback.textContent = "Chính xác!";
        } else {
            feedback.classList.add("feedback-wrong");
            feedback.textContent = "Chưa chính xác. Đáp án đúng đã được hiển thị.";
        }

        answerIsVisible = true;
        actionNote.textContent = "Đáp án đã hiển thị. Bấm Next để tiếp tục.";
        if (currentIndex === cards.length - 1) {
            nextButton.textContent = "Nộp bài →";
        } else {
            nextButton.textContent = "Next - Câu tiếp theo →";
        }
    }

    nextButton.addEventListener("click", () => {
        if (!answerIsVisible) {
            revealAnswer();
            return;
        }

        if (currentIndex === cards.length - 1) {
            cards.forEach((card) => {
                card.querySelectorAll("input").forEach((input) => {
                    input.disabled = false;
                });
            });
            form.submit();
            return;
        }

        currentIndex += 1;
        showCurrentCard();
    });

    showCurrentCard();
});
