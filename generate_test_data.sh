#!/bin/bash
# Simple Medical Document Generator Script
# Usage: ./generate_test_data.sh

echo "🏥 MEDICAL DOCUMENT GENERATOR"
echo "=============================="
echo ""

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama LLM: Connected"
else
    echo "❌ Ollama LLM: Not running"
    echo "Please start Ollama first: ollama serve"
    exit 1
fi

echo ""
echo "Select generation size:"
echo "1) Quick Test (3 patients, 3 reports each) - ~1 minute"
echo "2) Demo Dataset (10 patients, 5 reports each) - ~5 minutes"  
echo "3) Large Dataset (25 patients, 8 reports each) - ~15 minutes"
echo "4) Custom (specify your own)"
echo ""

read -p "Choose option [1-4]: " choice

case $choice in
    1)
        PATIENTS=3
        REPORTS=3
        echo "🚀 Generating Quick Test Dataset..."
        ;;
    2)
        PATIENTS=10
        REPORTS=5
        echo "🚀 Generating Demo Dataset..."
        ;;
    3)
        PATIENTS=25
        REPORTS=8
        echo "🚀 Generating Large Dataset..."
        ;;
    4)
        read -p "Number of patients: " PATIENTS
        read -p "Reports per patient: " REPORTS
        echo "🚀 Generating Custom Dataset..."
        ;;
    *)
        echo "Invalid option. Using Quick Test (3 patients, 3 reports)"
        PATIENTS=3
        REPORTS=3
        ;;
esac

echo ""
echo "Configuration:"
echo "  Patients: $PATIENTS"
echo "  Reports per patient: $REPORTS"
echo "  Total documents: $((PATIENTS * REPORTS * 2))"
echo "  Output: data/patient_documents/"
echo ""

# Run the generator
python tools/generate_medical_documents.py --patients $PATIENTS --reports-per-patient $REPORTS

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 GENERATION COMPLETE!"
    echo ""
    echo "📁 Documents created in: data/patient_documents/"
    echo "📋 Master index: data/patient_documents/document_index.json"
    echo ""
    echo "🔄 To use with VisitIQ application:"
    echo "   1. Restart your application"
    echo "   2. Enhanced patients will be automatically detected"
    echo "   3. Multi-format documents will be processed"
    echo ""
    echo "🚀 Ready to test enhanced medical document processing!"
else
    echo ""
    echo "❌ Generation failed. Check the error messages above."
fi
