# Custom Events

Custom events are used for communication between web components. Here is a list of all available events.

| Event                | Pages                 | Data                                                    | Description                                                                               |
| -------------------- | --------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| chat-response-start  | /chats                | (none)                                                  | When the streaming connection is opened                                                   |
| chat-response-end    | /chats                | title: string<br/>session_id: string                    | When the stream "end" event is sent from the server                                       |
| stop-streaming       | /chats                | (none)                                                  | When a user presses the stop-streaming button, or an unexpected disconnection has occured |
| chat-title-change    | /chats                | title: string<br/>session_id: string<br/>sender: string | When the chat title is changed by the user                                                |
| file-error           | /chats                | name: string                                            | If there is a file error                                                                  |
| upload-init          | /chats                | (none)                                                  | When a user clicks the upload button, so it can trigger the file input click event        |
