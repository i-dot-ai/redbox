//
// For guidance on how to create routes see:
// https://prototype-kit.service.gov.uk/docs/create-routes
//

const govukPrototypeKit = require('govuk-prototype-kit')
const router = govukPrototypeKit.requests.setupRouter()
const { randomUUID } = require('crypto');

/**
 * @param {Request} request
 * @param {boolean} isSummary
 * @returns {string} html
 */
const generateSelectedDocsHtml = (request, isSummary) => {
    let selectedSources = [];
    if (request.session.data.dataSource === 'claude' && !isSummary) {
        selectedSources.push('Large Language Model');
    } else {
        request.session.data.docs.forEach((doc) => {
            if (doc.selected) {
                selectedSources.push(doc.name);
            }
        });
    }
    if (!selectedSources.length) {
        selectedSources.push('None');
    }
    return `<dl><dt>Selected sources:</dt><dd>${selectedSources.toString().replace(/,/g, ', ')}</dd></dl>`;
};

/**
 * 
 * @param {Request} request 
 * @param {string} action
 */
const log = (request, action) => {
    let now = new Date();
    let to2units = (val) => {
        return val < 10 ? `0${val}` : val.toString()
    };
    request.session.data.logs.push({
        time: `${to2units(now.getDay())}/${to2units(now.getMonth() + 1)}/${now.getFullYear().toString().substring(2,4)} ${to2units(now.getHours())}:${to2units(now.getMinutes())}`,
        action: action
    });
};

/**
 * 
 * @param {Request} request 
 * @param {string} title 
 * @returns {number} chatIndex
 */
const createNewChat = (request, title) => {
    const MAX_TITLE_LENGTH_CHARACTERS = 35;
    let chats = request.session.data.chats;
    let chatTitle = title.length > MAX_TITLE_LENGTH_CHARACTERS ? title.slice(0, MAX_TITLE_LENGTH_CHARACTERS) + '...' : title;
    chats.push({
        title: chatTitle,
        messages: []
    });
    chatIndex = chats.length - 1;
    log(request, `New chat: <a href="chat?chat-index=${chatIndex}">${chatTitle}</a>`);
    return chatIndex;
};


router.post('/upload', (request, response) => {
    let redirectUrl = request.session.data['redirect-url'];
    let fileName = request.session.data.fileUpload.replace(/\.[^.]*$/, '');
    const formattedDate = () => {
        const today = new Date();
        const day = String(today.getDate()).padStart(2, '0');
        const month = String(today.getMonth() + 1).padStart(2, '0'); // Months are zero-based in JavaScript
        const year = today.getFullYear().toString().substring(2, 4);
        return `${day}/${month}/${year}`;
    };
    request.session.data.docs.push({
        selected: true,
        name: fileName,
        dateUploaded: formattedDate(),
        id: randomUUID(),
        processedPercent: 0
    });
    log(request, `Uploaded: ${fileName}`);
    response.redirect(redirectUrl);
});


router.get('/processing-doc-update', (request, response) => {
    let docIndex = request.session.data['doc-index'];
    let value = parseInt(request.session.data['process-percent']);
    request.session.data.docs[docIndex].processedPercent = value;
    response.end();
});


router.get('/confirm-delete', (request, response) => {
    let docId = request.session.data['doc-id'];
    let redirectUrl = request.session.data['redirect-url'];
    let docs = request.session.data.docs;
    
    // remove doc
    let docIndex = -1;
    docs.forEach((_doc, _docIndex) => {
        if (_doc.id === docId) {
            docIndex = _docIndex;
            log(request, `Removed: ${_doc.name}`);
        }
    });
    if (docIndex !== -1) {
        docs.splice(docIndex, 1);
    }

    response.redirect(redirectUrl);
});


router.post('/message', (request, response) => {
    let prototype = request.session.data.prototype;
    let message = request.session.data['new-message'].trim();
    let chatIndex = parseInt(request.session.data['chat-index'] || '-1');
    let chats = request.session.data.chats;

    if (message !== '') {

        // is this a new chat?
        if (chatIndex === -1 || chats.length < chatIndex - 1) {
            chatIndex = createNewChat(request, message);
        }

        // add the user message
        chats[chatIndex].messages.push({
            from: 'user', 
            text: `<p>${message}</p>`
        });

        // add an AI response
        chats[chatIndex].messages.push({
            from: 'redbox',
            text: `<p>This is the AI response to your message.</p><p>This is a demo, otherwise it would have been a more helpful response.</p>${generateSelectedDocsHtml(request, false)}`
        });

    }

    response.redirect(`/${prototype}/chat?chat-index=${chatIndex}`);
});

/*
router.all('/summary', (request, response) => {
    let chatIndex = parseInt(request.session.data['chat-index'] || '-1');
    // doc-index is only passed in if summarising a single doc from the data-source page
    let docIndex = parseInt(request.session.data['doc-index'] || '-1');
    let chats = request.session.data.chats;

    // is this a new chat?
    if (chatIndex === -1) {
        let chatTitle = 'Summarise selected documents';
        if (docIndex !== -1) {
            chatTitle = `Summarise doc: ${request.session.data.docs[docIndex].name}`;
        }
        chatIndex = createNewChat(request, chatTitle);
    }

    // if coming from the data-source page, deselect all but this one doc
    if (docIndex !== -1) {
        request.session.data.docs.forEach((doc, index) => {
            doc.selected = (index === docIndex);
        });
    }

    // add an AI response
    chats[chatIndex].messages.push({
        from: 'redbox',
        text: `<h2 class="govuk-heading-s">Overview</h2><p>Here is a summary of your selected documents. This is a demo summary which would provide helpful information.</p><h2 class="govuk-heading-s">Key Dates</h2><p>Any dates mentioned will be listed here.</p><a href="#download-summary">Download this summary</a>${generateSelectedDocsHtml(request, true)}`
    });

    response.redirect(`/${request.session.data.prototype}/chat?chat-index=${chatIndex}`);
});
*/

router.post('/toggle-document-selection', (request, response) => {
    let docId = request.session.data.index;
    let selected = request.session.data.selected;
    let type = request.session.data.type;
    request.session.data[type][docId].selected = (selected === 'true');
    response.end();
});


router.get('/toggle-data-source', (request, response) => {
    request.session.data.dataSource = request.session.data.source;
    response.end();
});


router.get('/new-chat', (request, response) => {
    // deselect all docs
    request.session.data.docs.forEach((doc, index) => {
        doc.selected = false;
    });
    response.redirect(`/${request.session.data.prototype}/chat?chat-index=-1`);
});