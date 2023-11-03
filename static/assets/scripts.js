document.addEventListener("DOMContentLoaded", function() {
    const chatLog = document.getElementById('chatLog');
    const userInput = document.getElementById('userInput');

    // Bind the Enter key to submit the question and bind the click event to the submit button
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            submitQuestion();
        }
    });

    const submitBtn = document.querySelector("button");
    if (submitBtn) {
        submitBtn.addEventListener("click", submitQuestion);
    }

    // Toggle sidebar
    const sidebar = document.querySelector('.sidebar');
    const navigatorBtn = document.querySelector('.navigator-button');
    navigatorBtn.addEventListener('click', () => {
        sidebar.classList.toggle('active');
    });
});

function submitQuestion() {
    const userInput = document.getElementById('userInput');
    const userText = userInput.value;

    if (userText.trim() === '') return;

    // Disable the button to prevent double submissions
    document.querySelector("button").disabled = true;

    // Add the user's message to the chat log with bounce animation
    const chatLog = document.getElementById('chatLog');
    const userMessage = document.createElement('p');

    userMessage.innerHTML = "<strong>You:</strong> " + userText;
    userMessage.className = 'user animate__animated animate__bounceIn';
    chatLog.appendChild(userMessage);

    // Scroll to the new message
    userMessage.scrollIntoView();

    // Clear the input field
    userInput.value = '';

    // Send a request to the server to get the AI's response
    fetch('/ask', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'message=' + encodeURIComponent(userText),
    })
    .then(response => response.json())
    .then(data => {
        // Re-enable the button
        document.querySelector("button").disabled = false;

        const aiMessage = document.createElement('p');
        aiMessage.innerHTML = "<strong>AI Evaluator:</strong> " + data.response;
        userMessage.className = 'user animate__animated animate__bounceIn';
        chatLog.appendChild(aiMessage);

        // Scroll to the AI's message
        aiMessage.scrollIntoView();
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
