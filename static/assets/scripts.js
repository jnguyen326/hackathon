document.addEventListener("DOMContentLoaded", function() {
    // Bind the submit event to the button
    const submitBtn = document.querySelector("button");
    if (submitBtn) {
        submitBtn.addEventListener("click", submitQuestion);
    }
});

function submitQuestion() {
    const userInput = document.getElementById('userInput').value;

    if (userInput.trim() === '') return;

    // Add the user's message to the chat log
    const chatLog = document.getElementById('chatLog');
    const userMessage = document.createElement('p');
    userMessage.innerHTML = "<strong>You:</strong> " + userInput;
    chatLog.appendChild(userMessage);

    // Send a request to the server to get the AI's response
    fetch('/ask', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'message=' + encodeURIComponent(userInput),
    })
    .then(response => response.json())
    .then(data => {
        const aiMessage = document.createElement('p');
        aiMessage.innerHTML = "<strong>AI Evaluator:</strong> " + data.response;
        chatLog.appendChild(aiMessage);
    });
}
