// ── Dark Mode ──────────────────────────────────────────────
const html = document.documentElement;
const themeToggle = document.getElementById('themeToggle');

function applyTheme(theme) {
    html.setAttribute('data-theme', theme);
    document.documentElement.style.colorScheme = theme === 'dark' ? 'dark' : 'light';
    localStorage.setItem('theme', theme);
    updateThemeButton();
}

function updateThemeButton() {
    if (!themeToggle) return;
    const isDark = html.getAttribute('data-theme') === 'dark';
    themeToggle.innerHTML = `<span class="me-2">${isDark ? '☽' : '☀'}</span><span>${isDark ? 'Dark' : 'Light'}</span>`;
}

const saved = localStorage.getItem('theme');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
const initialTheme = saved || (prefersDark ? 'dark' : 'light');
applyTheme(initialTheme);

themeToggle.addEventListener('click', () => {
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(next);
});

const resultSection = document.getElementById('resultSection');
const resultSuccess = document.getElementById('resultSuccess');
const resultError = document.getElementById('resultError');

function showSuccess(data) {
    resultError.style.display = 'none';
    resultSuccess.style.display = '';
    resultSection.style.display = '';

    document.getElementById('answerText').textContent = data.answer || 'No answer returned.';
    document.getElementById('contextText').textContent = data.context || 'No context returned.';
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showError(message) {
    resultSuccess.style.display = 'none';
    resultError.style.display = '';
    resultError.textContent = 'Error: ' + message;
    resultSection.style.display = '';
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

const form = document.getElementById('ragForm');
const btn = document.getElementById('askBtn');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = 'Asking…';

    const payload = new FormData(form);
    try {
        const response = await fetch('/ask', {
            method: 'POST',
            body: payload,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await response.json();
        if (data.success) {
            showSuccess(data);
        } else {
            showError(data.error || 'Something went wrong.');
        }
    } catch (err) {
        showError('Could not reach the server. Make sure Flask is running.');
    } finally {
        btn.disabled = false;
        btn.querySelector('.btn-text').textContent = 'Ask Document';
    }
});

window.addEventListener('DOMContentLoaded', () => {
    if (window.FLASK_RESULT) {
        if (window.FLASK_RESULT.success) {
            showSuccess(window.FLASK_RESULT);
        } else {
            showError(window.FLASK_RESULT.error || 'Something went wrong.');
        }
    }
});
