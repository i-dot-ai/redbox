// @ts-check

/** @type {import ('../node_modules/@types/alpinejs/index.d.ts').Alpine} */
let Alpine = window["Alpine"];


// Polls for updates to file statuses
Alpine.data('file-status', () => ({
    
    status: '',
    init() {

        this.status = this.$el.textContent || '';

        const checkStatus = async () => {
            
            // UPDATE THESE AS REQUIRED
            const FILE_STATUS_ENDPOINT = '/file-status';
            const CHECK_INTERVAL_MS = 5000;
            
            const response = await fetch(`${FILE_STATUS_ENDPOINT}?id=${this.$el.dataset.id}`);
            const responseText = await response.json();
            if (response.ok) {
                this.status = responseText["status"];
            }
            if (this.status !== 'complete') {
                window.setTimeout(checkStatus, CHECK_INTERVAL_MS);
            }

        };

        checkStatus();
    }

}));

