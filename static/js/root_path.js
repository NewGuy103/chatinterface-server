"use strict";


/**
 * @type {Map<string, string>}
 */
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
    const [ response, error ] = await safeFetch(fetch('/api/token/info', { method: "GET" }))

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
    const [ response, error ] = await safeFetch(fetch('/api/chats/recipients', { method: "GET" }))

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
        const apiUrl = '/api/chats/messages'
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
    const [ response, error ] = await safeFetch(fetch(`/api/chats/message/${messageId}`))
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
    const fetchCall = fetch('/api/chats/message', {
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
 * @param {string} messageId 
 * @param {string} messageData 
 */
async function updateChatMessage(messageId, messageData) {
    const reqBody = JSON.stringify({'message_data': messageData})
    const fetchCall = fetch(`/api/chats/message/${messageId}`, {
        method: "PATCH",
        headers: { 'Content-Type': 'application/json', 'accept': 'application/json' },
        body: reqBody
    })

    const [ response, error ] = await safeFetch(fetchCall)
    if (error) {
        console.error(`[updateChatMessage] Request failed: ${error}`)
        alert(`[updateChatMessage] Request failed: ${error}`)
        return null
    }
    if (!response.ok) {
        console.error(`[updateChatMessage] Failed with non-OK status code: ${response.status}`)
        alert(`[updateChatMessage] Failed with non-OK status code: ${response.status} `)
        return null
    }

    const successMessage = await response.json()
    if (!successMessage.success) {
        console.error(`[updateChatMessage] API Call was not successful: ${successMessage}`)
        alert(`[updateChatMessage] API Call was not successful: ${successMessage}`)
        return null
    }

    return successMessage
}
/**
 * @param {string} messageId 
 */
async function deleteChatMessage(messageId) {
    const fetchCall = fetch(`/api/chats/message/${messageId}`, {
        method: "DELETE",
        headers: { 'Content-Type': 'application/json', 'accept': 'application/json' }
    })

    const [ response, error ] = await safeFetch(fetchCall)
    if (error) {
        console.error(`[deleteChatMessage] Request failed: ${error}`)
        alert(`[deleteChatMessage] Request failed: ${error}`)
        return null
    }
    if (!response.ok) {
        console.error(`[deleteChatMessage] Failed with non-OK status code: ${response.status}`)
        alert(`[deleteChatMessage] Failed with non-OK status code: ${response.status} `)
        return null
    }

    const successMessage = await response.json()
    if (!successMessage.success) {
        console.error(`[deleteChatMessage] API Call was not successful: ${successMessage}`)
        alert(`[deleteChatMessage] API Call was not successful: ${successMessage}`)
        return null
    }

    return successMessage
    
}
/**
 * @param {string} recipientName 
 * @param {string} messageData 
 * @returns {Promise<string>} Returns a UUID.
 */
async function composeChatMessage(recipientName, messageData) {
    const reqBody = JSON.stringify({
        'recipient': recipientName,
        'message_data': messageData
    })
    const fetchCall = fetch('/api/chats/message/compose', {
        method: "POST",
        headers: { 'Content-Type': 'application/json', 'accept': 'application/json' },
        body: reqBody
    })

    const [ response, error ] = await safeFetch(fetchCall)
    if (error) {
        console.error(`[composeChatMessage] Request failed: ${error}`)
        alert(`[composeChatMessage] Request failed: ${error}`)
        return null
    }
    if (!response.ok) {
        console.error(`[composeChatMessage] Failed with non-OK status code: ${response.status}`)
        alert(`[composeChatMessage] Failed with non-OK status code: ${response.status} `)
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

    recipientsArray.forEach(username => appendRecipient(username))
    return true
}

/**
 * @param {string} username 
 */
function appendRecipient(username) {
    const recipientsBox = document.getElementById('recipients')

    const recipientItemDiv = document.createElement('div')
    const recipientNameText = document.createElement('p')

    recipientItemDiv.classList.add('recipient-item')
    recipientNameText.classList.add('recipient-username')

    recipientNameText.textContent = username
    recipientItemDiv.appendChild(recipientNameText)

    recipientsBox.appendChild(recipientItemDiv)
    recipientItemDiv.addEventListener("click", (ev) => switchToRecipient(ev, username))
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
        console.log("Data Received:", ev.data)
        if (jsonMsg === "OK") return  // websocket is ready

        switch (jsonMsg.message) {
            case "message.received":
                ws_messageReceived(jsonMsg.data)
                break;
            case "message.update":
                ws_messageUpdate(jsonMsg.data)
                break;
            case "message.delete":
                ws_messageDelete(jsonMsg.data)
                break;
            case "message.compose":
                ws_messageCompose(jsonMsg.data)
                break;
            case "auth.revoked":
                ws_authRevoked()
                break;
            case "ALIVE":
                // Add a function to use this
                break;
            default:
                console.error(`Invalid websocket message received: ${jsonMsg.message} | ${ev.data}`)
                break;
        }
    }
    websocket.onerror = (ev) => {
        console.error("WebSocket closed due to error:", ev.reason)
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
    const isSender = dataAsMap.get('sender_name') === sessionInfo.get('username')
    let messagesList, currentChatName;
    if (isSender) {
        const recipientName = dataAsMap.get('recipient_name')
        messagesList = messagesMap.get(recipientName)
        currentChatName = recipientName
    } else {
        currentChatName = dataAsMap.get('sender_name')
        messagesList = messagesMap.get(dataAsMap.get('sender_name'))
    }
    messagesList.push(dataAsMap)

    const topbarUsername = document.getElementsByClassName('topbar-recipient-username')[0]
    if (topbarUsername.textContent === currentChatName) {
        const options = new Map(Object.entries({
            is_sender: isSender
        }))
        appendMessage(dataAsMap, options)
    }
}

function ws_messageUpdate(data) {
    const dataAsMap = new Map(Object.entries(data))
    let messagesList, currentChatName;
    if (dataAsMap.get('sender_name') === sessionInfo.get('username')) {
        const recipientName = dataAsMap.get('recipient_name')
        messagesList = messagesMap.get(recipientName)
        currentChatName = recipientName
    } else {
        currentChatName = dataAsMap.get('sender_name')
        messagesList = messagesMap.get(dataAsMap.get('sender_name'))
    }
    messagesList.forEach((value) => {
        const messageId = value.get('message_id')
        if (messageId !== dataAsMap.get('message_id')) return

        value.set("message_data", dataAsMap.get('message_data'))
    })

    const topbarUsername = document.getElementsByClassName('topbar-recipient-username')[0]
    if (topbarUsername.textContent === currentChatName) {
        updateMessage(dataAsMap)
    }
}
function ws_messageDelete(data) {
    const dataAsMap = new Map(Object.entries(data))
    let messagesList, currentChatName;
    if (dataAsMap.get('sender_name') === sessionInfo.get('username')) {
        const recipientName = dataAsMap.get('recipient_name')
        messagesList = messagesMap.get(recipientName)
        currentChatName = recipientName
    } else {
        currentChatName = dataAsMap.get('sender_name')
        messagesList = messagesMap.get(dataAsMap.get('sender_name'))
    }
    console.log(currentChatName)
    const filtered = messagesList.filter((value) => {
        const messageId = value.get('message_id')
        if (messageId !== dataAsMap.get('message_id')) return true

        return false
    })
    messagesMap.set(currentChatName, filtered)
    deleteMessage(dataAsMap)
}
function ws_messageCompose(data) {
    const dataAsMap = new Map(Object.entries(data))
    const dataArray = [dataAsMap]
    let currentChatName;
    
    if (dataAsMap.get('sender_name') === sessionInfo.get('username')) {
        currentChatName = dataAsMap.get('recipient_name')
    } else {
        currentChatName = dataAsMap.get('sender_name')
    }
    messagesMap.set(currentChatName, dataArray)
    receiveComposedMessage(dataAsMap)
}
function ws_authRevoked() {
    alert("You have been logged out, please login again.")
    window.location.href = "/frontend/login"
}

/**
 * @param {Map<string, string>} messageData
 * @param {Map<string, any>} options 
 */
function appendMessage(messageData, options) {
    console.log(messageData, options)
    const messageId = messageData.get('message_id')
    const messagesBox = document.getElementsByClassName('messages-box')[0]

    const messageItemDiv = document.createElement('div')
    messageItemDiv.classList.add('message-item')
    messageItemDiv.classList.add(`message-${messageId}`)

    const messageUsernameText = document.createElement('p')
    messageUsernameText.classList.add('message-username')
    messageUsernameText.textContent = messageData.get('sender_name')

    const messageDataText = document.createElement('p')
    messageDataText.classList.add('message-text')
    messageDataText.textContent = messageData.get('message_data')

    const showDialogButton = document.createElement('button')
    showDialogButton.classList.add('options-button')
    showDialogButton.textContent = '...'

    const optionsDialog = document.createElement('dialog')
    optionsDialog.classList.add('options-dialog')

    const editMessageButton = document.createElement('button')
    editMessageButton.classList.add('edit-message-button')
    editMessageButton.textContent = 'Edit Message'

    const deleteMessageButton = document.createElement('button')
    deleteMessageButton.classList.add('delete-message-button')
    deleteMessageButton.textContent = 'Delete Message'

    showDialogButton.addEventListener('click', (ev) => {
        if (optionsDialog.open) {
            optionsDialog.style.display = 'none'
            optionsDialog.close()
        } else {
            optionsDialog.style.display = 'flex'
            optionsDialog.show()
        }
    })

    editMessageButton.addEventListener('click', async (ev) => {
        const originalMessage = messageData.get('message_data')
        const editedMessage = prompt("New message:", originalMessage)

        if (!editedMessage) return  // no data from user
        if (editedMessage === originalMessage) return  // unchanged

        const editSuccess = await updateChatMessage(messageId, editedMessage)
        if (!editSuccess) return
    })
    deleteMessageButton.addEventListener('click', async (ev) => {
        const deleteConfirmed = confirm("Delete this message?")
        if (!deleteConfirmed) return

        const deleteSuccess = await deleteChatMessage(messageId)
        if (!deleteSuccess) return
    })

    messageItemDiv.appendChild(messageUsernameText)
    messageItemDiv.appendChild(messageDataText)

    if (options.get('is_sender')) {
        optionsDialog.appendChild(editMessageButton)
        optionsDialog.appendChild(deleteMessageButton)
    
        messageItemDiv.appendChild(showDialogButton)
        messageItemDiv.appendChild(optionsDialog)
    }

    messagesBox.appendChild(messageItemDiv)
}

/**
 * 
 * @param {Map<string, string>} messageData 
 */
function updateMessage(messageData) {
    const messageId = messageData.get('message_id')
    const recipientUser = messageData.get('recipient_user')

    const messagesBox = document.getElementsByClassName('messages-box')[0]
    const messageItemDiv = messagesBox.getElementsByClassName(`message-${messageId}`)[0]

    const messageDataText = messageItemDiv.getElementsByClassName('message-text')[0]
    messageDataText.textContent = messageData.get('message_data')
}
/**
 * 
 * @param {Map<string, string>} messageData 
 */
function deleteMessage(messageData) {
    const messageId = messageData.get('message_id')

    const messagesBox = document.getElementsByClassName('messages-box')[0]
    const messageItemDiv = messagesBox.getElementsByClassName(`message-${messageId}`)[0]

    messagesBox.removeChild(messageItemDiv)
}
/**
 * @param {Map<string, string>} messageData 
 */
function receiveComposedMessage(messageData) {
    let currentChatName;
    
    if (messageData.get('sender_name') === sessionInfo.get('username')) {
        currentChatName = messageData.get('recipient_name')
        
    } else {
        currentChatName = messageData.get('sender_name')
    }

    appendRecipient(currentChatName)
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

    messageDataList.forEach((messageData) => {
        const senderName = messageData.get('sender_name')
        const options = new Map(Object.entries({
            is_sender: senderName === username ? false : true
        }))
        appendMessage(messageData, options)
    })
}

async function main() {
    sessionInfo = new Map(Object.entries(await getSessionInfo()))
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
    const composeMessageButton = document.getElementsByClassName('compose-message-button')[0]

    /**
     * @type {HTMLButtonElement}
     */
    const logoutButton = document.getElementsByClassName('logout-button')[0]

    /**
     * @type {HTMLDialogElement}
     */
    const composeDialog = document.getElementsByClassName('compose-dialog')[0]

    /**
     * @type {HTMLFormElement}
     */
    const composeDialogForm = document.getElementsByClassName('compose-dialog-form')[0]

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
    })

    composeMessageButton.addEventListener('click', (ev) => composeDialog.showModal())
    composeDialogForm.addEventListener('reset', (ev) => {
        composeDialog.close()
    })
    composeDialogForm.addEventListener('submit', async (ev) => {
        ev.preventDefault()
        composeDialog.close()
        const formData = new FormData(composeDialogForm)
        const jsonFormData = {}

        formData.forEach((val, key) => {
            jsonFormData[key] = val
        })

        if (!jsonFormData.recipient || !jsonFormData.message) return
        // clears the form
        for (let element of composeDialogForm.elements) {
            if (element.type !== "submit" && element.type !== "button") {
              element.value = "";
            }
        }

        const messageId = await composeChatMessage(jsonFormData.recipient, jsonFormData.message)
        if (!messageId) return
    })
    logoutButton.addEventListener('click', async (event) => {
        await safeFetch(fetch('/api/token/revoke_session', { method: 'POST' }))
        window.location.href = '/'
    })
    await main()
})
