/**
 * Chatbot Analyse Financière - Frontend JavaScript
 */

// Configuration API
const API_BASE = '/api';

// État de l'application
let conversationHistory = [];
let documents = [];

// =====================
// Navigation
// =====================

document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const viewId = btn.dataset.view;
        switchView(viewId);
    });
});

function switchView(viewId) {
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewId);
    });
    
    // Update views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.toggle('active', view.id === `${viewId}-view`);
    });
    
    // Load data for specific views
    if (viewId === 'documents') {
        loadDocuments();
    }
}

// =====================
// Chat Functionality
// =====================

const chatInput = document.getElementById('chat-input');
const chatMessages = document.getElementById('chat-messages');
const sendBtn = document.getElementById('send-btn');

// Auto-resize textarea
chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
});

// Send on Enter (Shift+Enter for new line)
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    
    // Remove welcome message if present
    const welcome = chatMessages.querySelector('.welcome-message');
    if (welcome) welcome.remove();
    
    // Add user message to UI
    addMessageToUI('user', message);
    
    // Show loading
    const loadingId = showLoading();
    
    // Get filters
    const yearFilter = document.getElementById('filter-year').value;
    const countryFilter = document.getElementById('filter-country').value;
    
    const filters = {};
    if (yearFilter) filters.year = parseInt(yearFilter);
    if (countryFilter) filters.country = countryFilter;
    
    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: message,
                conversation_history: conversationHistory.slice(-6),
                filters: Object.keys(filters).length > 0 ? filters : null,
                top_k: 5
            })
        });
        
        if (!response.ok) throw new Error('Erreur serveur');
        
        const data = await response.json();
        
        // Remove loading
        hideLoading(loadingId);
        
        // Add assistant message
        addMessageToUI('assistant', data.answer, data.citations, data.confidence_score, data.processing_time_ms);
        
        // Update conversation history
        conversationHistory.push({ role: 'user', content: message });
        conversationHistory.push({ role: 'assistant', content: data.answer });
        
    } catch (error) {
        hideLoading(loadingId);
        addMessageToUI('assistant', "Désolé, une erreur s'est produite. Veuillez réessayer.");
        console.error('Chat error:', error);
    }
}

function addMessageToUI(role, content, citations = [], confidence = null, time = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = role === 'user' ? '👤' : '🤖';
    
    let citationsHtml = '';
    if (citations && citations.length > 0) {
        citationsHtml = `
            <div class="message-citations">
                <strong>Sources:</strong>
                ${citations.map((c, i) => `
                    <div class="citation-item">
                        <span class="citation-badge">${i + 1}</span>
                        <span>${c.document_title}${c.year ? ` (${c.year})` : ''} - Page ${c.page_number}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    let metaHtml = '';
    if (confidence !== null && role === 'assistant') {
        const confidencePercent = Math.round(confidence * 100);
        metaHtml = `
            <div class="message-meta">
                <div class="confidence">
                    <span>Confiance:</span>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${confidencePercent}%"></div>
                    </div>
                    <span>${confidencePercent}%</span>
                </div>
                ${time ? `<span>${Math.round(time)}ms</span>` : ''}
            </div>
        `;
    }
    
    // Format content with markdown-like formatting
    const formattedContent = formatContent(content);
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-text">${formattedContent}</div>
            ${citationsHtml}
            ${metaHtml}
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatContent(text) {
    // Convert **bold** to <strong>
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Convert *italic* to <em>
    text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Convert [Source X] to styled badges
    text = text.replace(/\[Source\s*(\d+)\]/g, '<span class="citation-badge">$1</span>');
    // Convert newlines to <br> or <p>
    text = text.split('\n\n').map(p => `<p>${p}</p>`).join('');
    text = text.replace(/\n/g, '<br>');
    return text;
}

function showLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.id = 'loading-message';
    loadingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="loading">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            </div>
        </div>
    `;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return 'loading-message';
}

function hideLoading(id) {
    const loading = document.getElementById(id);
    if (loading) loading.remove();
}

// =====================
// Documents Management
// =====================

async function loadDocuments() {
    const grid = document.getElementById('documents-grid');
    grid.innerHTML = '<div class="loading"><div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div></div>';
    
    try {
        const response = await fetch(`${API_BASE}/documents`);
        documents = await response.json();
        
        if (documents.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📁</div>
                    <h3>Aucun document</h3>
                    <p>Importez des rapports PDF pour commencer</p>
                </div>
            `;
            return;
        }
        
        grid.innerHTML = documents.map(doc => `
            <div class="document-card">
                <div class="document-icon">📄</div>
                <div class="document-title">${doc.title || doc.filename}</div>
                <div class="document-meta">📅 ${doc.year || 'Année non spécifiée'}</div>
                <div class="document-meta">🌍 ${doc.country || 'Pays non spécifié'}</div>
                <div class="document-meta">📑 ${doc.total_pages} pages • ${doc.chunks_count} segments</div>
                <div class="document-actions">
                    <button class="btn-small danger" onclick="deleteDocument('${doc.filename}')">
                        🗑️ Supprimer
                    </button>
                </div>
            </div>
        `).join('');
        
        // Update filters
        updateFilters(documents);
        
    } catch (error) {
        grid.innerHTML = `<div class="empty-state"><p>Erreur de chargement</p></div>`;
        console.error('Load documents error:', error);
    }
}

function updateFilters(docs) {
    const years = [...new Set(docs.map(d => d.year).filter(Boolean))].sort();
    const countries = [...new Set(docs.map(d => d.country).filter(Boolean))].sort();
    
    const yearSelect = document.getElementById('filter-year');
    const countrySelect = document.getElementById('filter-country');
    
    yearSelect.innerHTML = '<option value="">Toutes</option>' + 
        years.map(y => `<option value="${y}">${y}</option>`).join('');
    
    countrySelect.innerHTML = '<option value="">Tous</option>' + 
        countries.map(c => `<option value="${c}">${c}</option>`).join('');
}

async function deleteDocument(filename) {
    if (!confirm(`Supprimer "${filename}" ?`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadDocuments();
            loadStats();
        }
    } catch (error) {
        console.error('Delete error:', error);
        alert('Erreur lors de la suppression');
    }
}

// =====================
// Upload Modal
// =====================

const uploadModal = document.getElementById('upload-modal');
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');

function showUploadModal() {
    uploadModal.classList.add('active');
    document.getElementById('file-name').textContent = '';
    fileInput.value = '';
}

function hideUploadModal() {
    uploadModal.classList.remove('active');
    document.getElementById('upload-progress').classList.remove('active');
}

// Drag and drop
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        document.getElementById('file-name').textContent = e.dataTransfer.files[0].name;
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
        document.getElementById('file-name').textContent = fileInput.files[0].name;
    }
});

async function uploadFile() {
    const file = fileInput.files[0];
    if (!file) {
        alert('Veuillez sélectionner un fichier');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const year = document.getElementById('upload-year').value;
    const country = document.getElementById('upload-country').value;
    const org = document.getElementById('upload-org').value;
    
    if (year) formData.append('year', year);
    if (country) formData.append('country', country);
    if (org) formData.append('organization', org);
    
    // Show progress
    document.getElementById('upload-progress').classList.add('active');
    document.getElementById('upload-btn').disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            hideUploadModal();
            loadDocuments();
            loadStats();
            alert(`Document importé avec succès!\n${data.chunks_created} segments créés.`);
        } else {
            throw new Error(data.message || 'Erreur upload');
        }
        
    } catch (error) {
        alert('Erreur lors de l\'import: ' + error.message);
        console.error('Upload error:', error);
    } finally {
        document.getElementById('upload-progress').classList.remove('active');
        document.getElementById('upload-btn').disabled = false;
    }
}

// =====================
// Analysis
// =====================

async function runAnalysis() {
    const indicators = document.getElementById('analyze-indicators').value
        .split(',').map(i => i.trim()).filter(Boolean);
    
    if (indicators.length === 0) {
        alert('Veuillez saisir au moins un indicateur');
        return;
    }
    
    const yearsInput = document.getElementById('analyze-years').value;
    const countriesInput = document.getElementById('analyze-countries').value;
    const analysisType = document.getElementById('analyze-type').value;
    
    const years = yearsInput ? yearsInput.split(',').map(y => parseInt(y.trim())).filter(Boolean) : null;
    const countries = countriesInput ? countriesInput.split(',').map(c => c.trim()).filter(Boolean) : null;
    
    const resultsDiv = document.getElementById('analyze-results');
    resultsDiv.innerHTML = '<div class="loading"><div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div></div>';
    
    try {
        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                indicators,
                years,
                countries,
                analysis_type: analysisType
            })
        });
        
        const data = await response.json();
        
        const formattedAnalysis = formatContent(data.analysis);
        
        let citationsHtml = '';
        if (data.citations && data.citations.length > 0) {
            citationsHtml = `
                <div class="message-citations" style="margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border-color);">
                    <strong>Sources utilisées:</strong>
                    ${data.citations.map((c, i) => `
                        <div class="citation-item">
                            <span class="citation-badge">${i + 1}</span>
                            <span>${c.document_title}${c.year ? ` (${c.year})` : ''} - Page ${c.page_number}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        resultsDiv.innerHTML = `
            <div class="analysis-result">
                <h3>📊 Résultats de l'analyse</h3>
                <div class="analysis-content">${formattedAnalysis}</div>
                ${citationsHtml}
            </div>
        `;
        
    } catch (error) {
        resultsDiv.innerHTML = `<div class="empty-state"><p>Erreur lors de l'analyse</p></div>`;
        console.error('Analysis error:', error);
    }
}

// =====================
// Stats
// =====================

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();
        
        document.getElementById('stat-docs').textContent = stats.total_documents;
        document.getElementById('stat-chunks').textContent = stats.total_chunks;
        
    } catch (error) {
        console.error('Stats error:', error);
    }
}

// =====================
// Init
// =====================

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadDocuments();
});

// Close modal on outside click
uploadModal.addEventListener('click', (e) => {
    if (e.target === uploadModal) {
        hideUploadModal();
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideUploadModal();
    }
});
