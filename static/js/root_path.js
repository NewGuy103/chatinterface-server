"use strict";

let sessionInfo;

/**
 * @type {Map<string, Array<Map<string, string>>>}
 */
let messagesMap;

/**
 * @type {WebSocket}
 */
let websocket;

/**
 * @param {Promise<Response>} fetchPromise
 * @returns {Promise<[Response | null, Error | null]>}
 */
async function safeFetch(fetchPromise) {
    try {
        const response = await fetchPromise
        return [response, null]
    } catch (err) {
        return [null, err]
    }
}

async function getSessionInfo() {
    const [ response, error ] = await safeFetch(fetch('/api/token/session_info', { method: "GET" }))

    if (error) {
        console.error(`[getSessionInfo] Response failed: ${error}`)
        alert(`[getSessionInfo] Response failed: ${error}`)
        return null
    }
    if (!response.ok) {
        console.error(`[getSessionInfo] Failed with non-OK status code: ${response.status}`)
        alert(`[getSessionInfo] Failed with non-OK status code: ${response.status}`)
        return null
    }

    const sessionInfo = await response.json()
    return sessionInfo
}


/**
 * @returns {Promise<Array<string>>}
 */
async function getRecipientsList() {
    const [ response, error ] = await safeFetch(fetch('/api/chats/retrieve_recipients', { method: "GET" }))

    if (error) {
        console.error(`[getRecipientsList] Request failed failed: ${error}`)
        alert(`[getRecipientsList] Request failed: ${error}`)
        return null
    }
    if (!response.ok) {
        console.error(`[getRecipientsList] Failed with non-OK status code: ${response.status}`)
        alert(`[getRecipientsList] Failed with non-OK status code: ${response.status}`)
        return null
    }

    const recipientsList = await response.json()
    return recipientsList
}

/**
 * @param {Array} recipientsList 
 */
async function getPreviousMessages(recipientsList) {
    const messagesMap = new Map()

    const successList = []
    const failList = []

    recipientsList.forEach(async (username) => {
        const apiUrl = '/api/chats/retrieve_messages'
        const params = new URLSearchParams({
            recipient: username,
            amount: 100
        })
        const [ response, error ] = await safeFetch(fetch(
            `${apiUrl}?${params}`, { method: 'GET' }
        ))

        if (error || !response.ok) {
            failList.push(username)
            return
        }

        successList.push(username)

        /**
         * @type {Array}
         */
        const messageJson = await response.json()
        const messageList = []

        messageJson.forEach((value, index) => {
            messageList[index] = new Map(Object.entries(value))
        })

        const reversedList = messageList.toReversed()
        messagesMap.set(username, reversedList)
    })
    if (failList.length) {
        const jsonFailList = JSON.stringify(failList)
        if (successList.length) {
            console.error(`[getPreviousMessages] Requests failed for recipients: ${jsonFailList}`)
            alert(`[getPreviousMessages] Requests failed for recipients: ${jsonFailList}`)
        } else {
            console.error(`[getPreviousMessages] Requests failed for all recipients`)
            alert(`[getPreviousMessages] Requests failed for all recipients`)
        }
        return
    }

    return messagesMap
}


/**
 * @param {string} messageId 
 * @returns {Promise<Map<string, string>>}
 */
async function getMessageById(messageId) {
    const [ response, error ] = await safeFetch(fetch(`/api/chats/get_message/${messageId}`))
    if (error) {
        console.error(`[getMessageById] Request failed: ${error}`)
        alert(`[getMessageById] Request failed: ${error}`)
        return null
    }
    if (!response.ok) {
        console.error(`[getMessageById] Failed with non-OK status code: ${response.status}`)
        alert(`[getMessageById] Failed with non-OK status code: ${response.status}`)
        return null
    }

    const messageData = await response.json()
    return new Map(Object.entries(messageData))
}
/**
 * 
 * @param {string} recipientName 
 * @param {string} messageData 
 * @returns {Promise<string>} Returns a UUID.
 */
async function sendChatMessage(recipientName, messageData) {
    const reqBody = JSON.stringify({
        'recipient': recipientName,
        'message_data': messageData
    })
    const fetchCall = fetch('/api/chats/send_message', {
        method: "POST",
        headers: { 'Content-Type': 'application/json', 'accept': 'application/json' },
        body: reqBody
    })
    const [ response, error ] = await safeFetch(fetchCall)
    if (error) {
        console.error(`[sendChatMessage] Request failed: ${error}`)
        alert(`[sendChatMessage] Request failed: ${error}`)
        return null
    }
    if (!response.ok) {
        console.error(`[sendChatMessage] Failed with non-OK status code: ${response.status} ${JSON.stringify(await response.json())}`)
        alert(`[sendChatMessage] Failed with non-OK status code: ${response.status} `)
        return null
    }

    const successMessage = await response.json()
    return successMessage
}
/**
 * @param {Array<string>} recipientsArray 
 * @returns {boolean}
 */
function addRecipients(recipientsArray) {
    const recipientsBox = document.getElementById('recipients')
    if (!recipientsBox) throw new Error("Recipients box not found")

    recipientsArray.forEach(username => {
        const recipientItemDiv = document.createElement('div')
        const recipientNameText = document.createElement('p')

        recipientItemDiv.classList.add('recipient-item')
        recipientNameText.classList.add('recipient-username')

        recipientNameText.textContent = username
        recipientItemDiv.appendChild(recipientNameText)

        recipientsBox.appendChild(recipientItemDiv)
        recipientItemDiv.addEventListener("click", (ev) => switchToRecipient(ev, username))
    })

    return true
}

/**
 * @param {string} websocketPath
 */
function createWebsocket(websocketPath) {
    const websocket = new WebSocket(websocketPath)
    websocket.onopen = (ev) => {
        setInterval(ws_keepAlive, 5000)
    }
    websocket.onmessage = (ev) => {
        const jsonMsg = JSON.parse(ev.data)
        console.log(ev.data, "<<DAta")
        if (jsonMsg === "OK") return  // websocket is ready

        switch (jsonMsg.message) {
            case "message.received":
                ws_messageReceived(jsonMsg.data)
                break;
            case "ALIVE":
                // Add a function to use this
                break;
            default:
                console.error(`Invalid websocket message received: ${jsonMsg.message}`)
                break;
        }
    }

    return websocket
}

function ws_keepAlive() {
    if (!websocket) throw new Error("websocket not initalized")
    const keepaliveMessage = {
        'message': 'keepalive',
        'data': {}
    }
    websocket.send(JSON.stringify(keepaliveMessage))
}

function ws_messageReceived(data) {
    const dataAsMap = new Map(Object.entries(data))
    const newMessagesList = messagesMap.get(dataAsMap.get('sender_name'))
    newMessagesList.push(dataAsMap)

    const topbarUsername = document.getElementsByClassName('topbar-recipient-username')[0]
    if (topbarUsername.textContent === dataAsMap.get('sender_name')) {
        appendMessage(dataAsMap)
    }
}

/**
 * @param {Map<string, string>} messageData 
 */
function appendMessage(messageData) {
    const messagesBox = document.getElementById('messages-box')

    const messageItemDiv = document.createElement('div')
    const messageUsernameText = document.createElement('p')

    const messageDataText = document.createElement('p')
    messageItemDiv.classList.add('message-item')

    messageUsernameText.classList.add('message-username')
    messageUsernameText.textContent = messageData.get('sender_name')

    messageDataText.textContent = messageData.get('message_data')
    messageDataText.classList.add('message-text')

    messageItemDiv.appendChild(messageUsernameText)
    messageItemDiv.appendChild(messageDataText)

    messagesBox.appendChild(messageItemDiv)
}

/**
 * @param {MouseEvent} ev 
 * @param {string} username 
 */
function switchToRecipient(ev, username) {
    const messagesBox = document.getElementById('messages-box')
    while (messagesBox.firstChild) {
        messagesBox.firstChild.remove()
    }
    const topbarUsername = document.getElementsByClassName('topbar-recipient-username')[0]
    topbarUsername.textContent = username

    const messageDataList = messagesMap.get(username)
    if (!username) throw new Error("Missing recipient username in messagesMap")

    messageDataList.forEach((messageData) => appendMessage(messageData))
}

async function main() {
    sessionInfo = await getSessionInfo()
    if (!sessionInfo) return

    const recipientsList = await getRecipientsList()
    if (!recipientsList) return

    const addSuccess = addRecipients(recipientsList)
    if (!addSuccess) return

    messagesMap = await getPreviousMessages(recipientsList)
    if (!messagesMap) return

    websocket = createWebsocket('/api/ws/chat')
    if (!websocket) return
}

document.addEventListener('DOMContentLoaded', async (ev) => {
    const sendForm = document.getElementById('message-send-form')

    sendForm.addEventListener('submit', async (event) => {
        event.preventDefault()
        const topbarUsername = document.getElementsByClassName('topbar-recipient-username')[0]

        const formData = new FormData(sendForm)
        const jsonFormData = {}

        formData.forEach((val, key) => {
            jsonFormData[key] = val
        })

        if (!jsonFormData.message) return
        
        // clears the form
        for (let element of sendForm.elements) {
            if (element.type !== "submit" && element.type !== "button") {
              element.value = "";
            }
        }

        const messageId = await sendChatMessage(topbarUsername.textContent, jsonFormData.message)
        if (!messageId) return

        const messageData = await getMessageById(messageId)
        if (!messageData) return

        const newMessagesList = messagesMap.get(topbarUsername.textContent)
        newMessagesList.push(messageData)

        appendMessage(messageData)
    })
    await main()
})
