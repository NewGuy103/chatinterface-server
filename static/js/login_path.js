"use strict";


/**
 * @param {FormData} formData
 */
async function loginToServer(formData) {
    const loginResponseStatus = document.getElementById('login-response-status')
    let response;
    try {
        response = await fetch('/api/token/', {
            method: "POST",
            body: formData
        })
    } catch (error) {
        loginResponseStatus.textContent = `Fetch call to server failed: ${error}`
        return
    }

    const resData = await response.json()
    switch (response.status) {
        case 200:
            loginResponseStatus.textContent = "Login successful! Now redirecting..."            
            loginResponseStatus.style.color = 'green'
            window.location.href = "/frontend/"
            break;
        case 401:
            loginResponseStatus.textContent = "Error: Invalid username or password"
            loginResponseStatus.style.color = 'red'
            break;
        default:
            loginResponseStatus.textContent = `Unexpected server response code: ${response.status}`
            loginResponseStatus.style.color = 'red'
            break;
    }
}
document.addEventListener("DOMContentLoaded", (ev) => {
    const loginForm = document.getElementById('login-form')
    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const formData = new FormData(loginForm)
        await loginToServer(formData)
    })
})