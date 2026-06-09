document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("quiz-form");
    if (!form) return;

    const cards = Array.from(form.querySelectorAll(".question-card"));
    const progressElements = [
        document.getElementById("quiz-progress"),
        document.getElementById("quiz-progress-bottom"),
    ].filter(Boolean);

    function answeredCount() {
        return cards.filter((card) => card.querySelector("input:checked")).length;
    }

    function updateProgress() {
        const text = `Đã trả lời ${answeredCount()}/${cards.length} câu`;
        progressElements.forEach((element) => {
            element.textContent = text;
        });
    }

    form.addEventListener("change", updateProgress);
    form.addEventListener("submit", (event) => {
        const unanswered = cards.length - answeredCount();
        if (
            unanswered > 0 &&
            !window.confirm(`Bạn còn ${unanswered} câu chưa trả lời. Bạn vẫn muốn nộp bài?`)
        ) {
            event.preventDefault();
        }
    });

    updateProgress();
});

