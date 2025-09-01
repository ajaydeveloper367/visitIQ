#!/bin/bash
# Test Your Own Multi-Format Medical Documents
# Usage: ./test_your_documents.sh

echo "🏥 TESTING YOUR OWN MEDICAL DOCUMENTS"
echo "===================================="
echo ""

# Check if patient directory exists
if [ ! -d "data/patient_documents" ]; then
    echo "📁 Creating patient documents directory..."
    mkdir -p data/patient_documents
fi

echo "📋 INSTRUCTIONS FOR TESTING YOUR DOCUMENTS:"
echo ""
echo "1. 📁 CREATE PATIENT FOLDER:"
echo "   mkdir -p data/patient_documents/patient_<ID>"
echo "   Example: mkdir -p data/patient_documents/patient_101"
echo ""

echo "2. 📂 CREATE DOCUMENT CATEGORIES:"
echo "   mkdir -p data/patient_documents/patient_101/lab_reports"
echo "   mkdir -p data/patient_documents/patient_101/imaging"  
echo "   mkdir -p data/patient_documents/patient_101/vitals"
echo "   mkdir -p data/patient_documents/patient_101/clinical_notes"
echo "   mkdir -p data/patient_documents/patient_101/discharge_summaries"
echo ""

echo "3. 📄 COPY YOUR DOCUMENTS:"
echo "   • PDF Reports → lab_reports/"
echo "   • Images (JPG/PNG) → imaging/"
echo "   • JSON Vitals → vitals/"
echo "   • Text Notes → clinical_notes/"
echo "   • Word Documents → discharge_summaries/"
echo ""

echo "4. 🔄 TEST PROCESSING:"
echo "   python -c \"from src.medical_document_processor import MedicalDocumentProcessor; processor = MedicalDocumentProcessor(); result = processor.process_all_patient_documents('101'); print('Documents processed:', result['document_count'])\""
echo ""

echo "5. 🎯 VIEW IN VISITIQ:"
echo "   • Restart application: ./visitiq restart"
echo "   • Enhanced patients auto-detected"
echo "   • Multi-format data used in prioritization"
echo ""

echo "📊 SUPPORTED FORMATS:"
echo "   ✅ .pdf (Lab reports, clinical summaries)"
echo "   ✅ .jpg/.png (X-rays, scanned documents with OCR)"
echo "   ✅ .json (Structured vitals data)"
echo "   ✅ .txt (Clinical notes, observations)"
echo "   ✅ .docx (Word documents)"
echo "   ✅ .dcm (DICOM medical imaging - metadata)"
echo ""

echo "💡 EXAMPLE COMMANDS:"
echo ""
echo "# Create test patient 101"
echo "mkdir -p data/patient_documents/patient_101/{lab_reports,imaging,vitals,clinical_notes}"
echo ""
echo "# Copy your documents"  
echo "cp /path/to/your/lab_report.pdf data/patient_documents/patient_101/lab_reports/"
echo "cp /path/to/your/xray_image.jpg data/patient_documents/patient_101/imaging/"
echo "cp /path/to/your/vitals.json data/patient_documents/patient_101/vitals/"
echo "cp /path/to/your/notes.txt data/patient_documents/patient_101/clinical_notes/"
echo ""
echo "# Test processing"
echo "python test_multi_format_documents.py"
echo ""
echo "# View results in application"
echo "./visitiq restart"
echo ""

echo "🎉 READY TO PROCESS YOUR REAL MEDICAL DOCUMENTS!"
