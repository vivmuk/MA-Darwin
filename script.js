const pdfInput = document.getElementById('pdfInput');
const fileName = document.getElementById('fileName');
const statusMessage = document.getElementById('statusMessage');
const pdfPreview = document.getElementById('pdfPreview');

pdfInput.addEventListener('change', (event) => {
  const file = event.target.files[0];

  if (!file) {
    return;
  }

  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');

  if (!isPdf) {
    statusMessage.textContent = 'Please select a valid PDF file.';
    fileName.textContent = 'None';
    pdfPreview.src = 'about:blank';
    return;
  }

  const objectUrl = URL.createObjectURL(file);
  fileName.textContent = file.name;
  pdfPreview.src = objectUrl;
  statusMessage.textContent = 'PDF loaded successfully.';
});
