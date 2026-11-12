// Image to PDF conversion
let currentImages = [];
let uploadDir = null;

// API configuration — same origin (the backend serves the frontend),
// so relative URLs work no matter if the page is opened via
// http://127.0.0.1:8010 or http://localhost:8010
const API_BASE_URL = '';

// Each tool section has its own status/result containers.
// Writing to the wrong (hidden) container makes the UI look "frozen",
// so every helper below must know which section it is showing.
const SECTION_UI = {
    images:    { status: 'statusContainer',          text: 'statusText',          result: 'resultContainer' },
    watermark: { status: 'watermarkStatusContainer', text: 'watermarkStatusText', result: 'watermarkResultContainer' },
    word:      { status: 'pdfToWordStatusContainer', text: 'pdfToWordStatusText', result: 'pdfToWordResultContainer' }
};

// Tool navigation functions
function showHome() {
    document.querySelectorAll('.tool-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById('home').classList.add('active');
    resetAllSections();
}

function showTool(tool) {
    document.querySelectorAll('.tool-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(tool).classList.add('active');
    resetAllSections();
}

function resetAllSections() {
    // Hide all status and result containers
    document.querySelectorAll('.status-container, .result-container').forEach(el => {
        el.style.display = 'none';
    });
}

// Image upload handling
function handleImageUpload(input) {
    const files = input.files;
    if (files.length === 0) return;
    
    showImagePreviewContainer();
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const reader = new FileReader();
        
        reader.onload = function(e) {
            currentImages.push({
                file: file,
                preview: e.target.result,
                name: file.name,
                size: file.size,
                id: Date.now() + i
            });
            renderImageList();
        };
        
        reader.readAsDataURL(file);
    }
}

function renderImageList() {
    const container = document.getElementById('imageList');
    container.innerHTML = '';
    
    currentImages.forEach(img => {
        const item = document.createElement('div');
        item.className = 'image-item';
        item.innerHTML = `
            <img src="${img.preview}" class="image-thumbnail" alt="${img.name}">
            <div class="image-info">
                <p>${img.name}</p>
                <p>${(img.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
            <button class="remove-image-btn" onclick="removeImage(${img.id})">حذف</button>
        `;
        container.appendChild(item);
    });
}

function removeImage(imageId) {
    currentImages = currentImages.filter(img => img.id !== imageId);
    renderImageList();
}

function showImagePreviewContainer() {
    document.getElementById('imagePreviewContainer').style.display = 'block';
}

// Image reordering
function reorderImages(direction) {
    // This would implement reordering functionality
    console.log('Reorder images:', direction);
    // For now, just show a message
    showMessage('امکان تغییر ترتیب تصاویر در این نسخه در دست توسعه است', 'warning');
}

// Convert images to PDF
async function convertImagesToPDF() {
    const outputName = document.getElementById('outputFilename').value;
    const pageSize = document.getElementById('pageSize').value;
    const orientation = document.getElementById('orientation').value;
    const margin = parseInt(document.getElementById('margin').value);
    
    if (currentImages.length === 0) {
        showMessage('لطفاً حداقل یک تصویر انتخاب کنید', 'error');
        return;
    }
    
    showStatus('در حال تبدیل تصاویر به PDF...', 'processing', 'images');
    
    try {
        // Upload images first
        const uploadResponse = await uploadImages(currentImages);
        
        // Convert to PDF
        const formData = new FormData();
        currentImages.forEach(img => {
            formData.append('files', img.file);
        });
        formData.append('output_name', outputName);
        formData.append('page_size', pageSize);
        formData.append('orientation', orientation);
        formData.append('margin', margin.toString());
        
        const convertResponse = await fetch(`${API_BASE_URL}/api/images-to-pdf/convert`, {
            method: 'POST',
            body: formData
        });
        
        if (!convertResponse.ok) {
            const error = await convertResponse.text();
            throw new Error(error);
        }
        
        // Get the PDF file
        const pdfBlob = await convertResponse.blob();
        const pdfUrl = URL.createObjectURL(pdfBlob);
        
        showStatus('تبدیل با موفقیت انجام شد!', 'success', 'images');
        showResult(pdfUrl, 'pdf', 'images', outputName, pdfBlob);

    } catch (error) {
        showStatus('خطا در تبدیل: ' + error.message, 'error', 'images');
    }
}

// Ask the backend for the real page count of the selected PDF
async function fetchPDFPageCount(file, uploadEndpoint, targetId) {
    const target = document.getElementById(targetId);
    try {
        const formData = new FormData();
        formData.append('file', file);
        const response = await fetch(`${API_BASE_URL}${uploadEndpoint}`, {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error('upload failed');
        const data = await response.json();
        const sizeMB = (file.size / 1024 / 1024).toFixed(2);
        if (data.page_count && data.page_count > 0) {
            target.textContent = `تعداد صفحات: ${data.page_count} | حجم: ${sizeMB} مگابایت`;
        } else {
            target.textContent = `تعداد صفحات قابل خواندن نیست (فایل اسکنی یا محافظت‌شده؟) | حجم: ${sizeMB} مگابایت`;
        }
    } catch (error) {
        const sizeMB = (file.size / 1024 / 1024).toFixed(2);
        target.textContent = `حجم: ${sizeMB} مگابایت`;
    }
}

// PDF upload handling
async function handlePDFFileInput(input, tool) {
    const file = input.files[0];
    if (!file) return;

    if (tool === 'pdf-watermark-removal') {
        showPDFPreviewContainer();
        document.getElementById('pdfFilename').textContent = file.name;
        document.getElementById('pdfPageCount').textContent = 'در حال خواندن فایل...';
        await fetchPDFPageCount(file, '/api/watermark-removal/upload', 'pdfPageCount');
    } else if (tool === 'pdf-to-word') {
        showPDFOptionsContainer();
        document.getElementById('pdfToWordFilename').textContent = file.name;
        document.getElementById('pdfToWordPageCount').textContent = 'در حال خواندن فایل...';
        await fetchPDFPageCount(file, '/api/pdf-to-word/upload', 'pdfToWordPageCount');
    }
}

function showPDFPreviewContainer() {
    document.getElementById('pdfPreviewContainer').style.display = 'block';
}

function showPDFOptionsContainer() {
    document.getElementById('pdfOptionsContainer').style.display = 'block';
}

// PDF to Word conversion
async function convertPdfToWord() {
    const fileInput = document.getElementById('pdfToWordInput');
    const outputName = document.getElementById('wordOutputFilename').value;
    const pageRange = document.getElementById('pageRange').value;
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showMessage('لطفاً یک فایل PDF انتخاب کنید', 'error', 'word');
        return;
    }

    showStatus('در حال تبدیل PDF به Word...', 'processing', 'word');
    
    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('output_name', outputName);
        formData.append('page_range', pageRange);
        
        const response = await fetch(`${API_BASE_URL}/api/pdf-to-word/convert`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(error);
        }
        
        const docxBlob = await response.blob();
        const docxUrl = URL.createObjectURL(docxBlob);
        
        showStatus('تبدیل با موفقیت انجام شد!', 'success', 'word');
        showResult(docxUrl, 'docx', 'word', outputName, docxBlob);

    } catch (error) {
        showStatus('خطا در تبدیل: ' + error.message, 'error', 'word');
    }
}

// Watermark removal
async function removeWatermark() {
    const fileInput = document.getElementById('pdfInput');
    const outputName = document.getElementById('watermarkOutputFilename').value;
    const method = document.getElementById('removalMethod').value;
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showMessage('لطفاً یک فایل PDF انتخاب کنید', 'error', 'watermark');
        return;
    }

    showStatus('در حال حذف واترمارک...', 'processing', 'watermark');
    
    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('output_name', outputName);
        formData.append('method', method);
        
        const response = await fetch(`${API_BASE_URL}/api/watermark-removal/remove`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(error);
        }
        
        const pdfBlob = await response.blob();
        const pdfUrl = URL.createObjectURL(pdfBlob);
        
        showStatus('واترمارک با موفقیت حذف شد!', 'success', 'watermark');
        showResult(pdfUrl, 'pdf', 'watermark', outputName, pdfBlob);

    } catch (error) {
        showStatus('خطا در حذف واترمارک: ' + error.message, 'error', 'watermark');
    }
}

// Status and result handling (section-aware)
function showStatus(message, type = 'processing', section = 'images') {
    const ui = SECTION_UI[section] || SECTION_UI.images;
    const container = document.getElementById(ui.status);
    const statusText = document.getElementById(ui.text);
    const indicator = container.querySelector('.status-indicator');

    container.style.display = 'flex';
    statusText.textContent = message;
    if (indicator) {
        indicator.className = 'status-indicator';
        indicator.classList.add(type);
    }
}

function showMessage(message, type = 'info', section = 'images') {
    showStatus(message, type, section);
    const ui = SECTION_UI[section] || SECTION_UI.images;
    setTimeout(() => {
        document.getElementById(ui.status).style.display = 'none';
    }, 3000);
}

function showResult(fileUrl, fileType, section = 'images', filename = null, blob = null) {
    const ui = SECTION_UI[section] || SECTION_UI.images;
    document.getElementById(ui.result).style.display = 'block';

    // Store the file URL for download
    window.currentResultUrl = fileUrl;
    window.currentResultType = fileType;
    window.currentResultSection = section;
    window.currentResultName = filename;
    window.currentResultBlob = blob;
}

function downloadResult() {
    if (!window.currentResultUrl) return;

    const fallback = window.currentResultType === 'pdf' ? 'output.pdf' : 'output.docx';
    const filename = window.currentResultName || fallback;
    const link = document.createElement('a');
    link.href = window.currentResultUrl;
    link.download = filename;
    link.click();
}

// Save the produced file to a location chosen by the user.
// Uses the browser's "Save as" dialog when available (Chrome/Edge);
// otherwise falls back to a normal download into the Downloads folder.
async function saveFileToDevice(section, defaultName, pickerTypes) {
    if (!window.currentResultUrl) return;

    let blob = window.currentResultBlob || null;
    if (!blob) {
        try {
            blob = await fetch(window.currentResultUrl).then(r => r.blob());
        } catch (error) {
            blob = null;
        }
    }

    if (blob && window.showSaveFilePicker) {
        try {
            const handle = await window.showSaveFilePicker({
                suggestedName: defaultName,
                types: pickerTypes
            });
            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();
            showMessage('فایل در محل انتخاب‌شده ذخیره شد', 'success', section);
            return;
        } catch (error) {
            // User closed the dialog without saving -> do nothing
            if (error && error.name === 'AbortError') return;
            // Otherwise fall through to the plain download fallback
        }
    }

    const link = document.createElement('a');
    link.href = window.currentResultUrl;
    link.download = defaultName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    showMessage('فایل در پوشه Downloads ذخیره شد', 'success', section);
}

function saveResult() {
    saveFileToDevice('images', window.currentResultName || 'output.pdf',
        [{ description: 'PDF', accept: { 'application/pdf': ['.pdf'] } }]);
}

function saveWatermarkResult() {
    saveFileToDevice('watermark', window.currentResultName || 'clean.pdf',
        [{ description: 'PDF', accept: { 'application/pdf': ['.pdf'] } }]);
}

function saveWordResult() {
    saveFileToDevice('word', window.currentResultName || 'output.docx',
        [{ description: 'Word Document', accept: { 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] } }]);
}

function downloadWatermarkResult() {
    if (!window.currentResultUrl) return;

    const link = document.createElement('a');
    link.href = window.currentResultUrl;
    link.download = window.currentResultName || 'clean.pdf';
    link.click();
}

function downloadWordResult() {
    if (!window.currentResultUrl) return;

    const link = document.createElement('a');
    link.href = window.currentResultUrl;
    link.download = window.currentResultName || 'output.docx';
    link.click();
}

async function uploadImages(images) {
    // This would be a more sophisticated upload process
    // For now, return a mock upload directory
    return { temp_dir: 'temp_' + Date.now() };
}

// Initialize
function init() {
    // Add event listeners to file inputs
    document.getElementById('imageInput').addEventListener('change', function() {
        handleImageUpload(this);
    });
    
    document.getElementById('pdfInput').addEventListener('change', function() {
        handlePDFFileInput(this, 'pdf-watermark-removal');
    });
    
    document.getElementById('pdfToWordInput').addEventListener('change', function() {
        handlePDFFileInput(this, 'pdf-to-word');
    });
    
    // Initialize with home view
    showHome();
}

// Start the application
init();