"""
Response templates for various agents
"""

# Document Classifier Response Templates
DOCUMENT_CLASSIFIER_TEMPLATES = {
    "NO_DOCUMENT_KEY": """No document key found for this session. Please upload the document again. Session ID: {session_id}""",
    
    "CLASSIFICATION_CONFIRMED_SUCCESS": """Document Classification Confirmed.\nDocument Type: **{doc_type}**. The document is now being uploaded for extraction. Please wait 1-2 minutes, then check the retrieval page to see if it has been extracted. If the document is not found, include the filename in your query.""",
    
    "CLASSIFICATION_CONFIRMED_SUCCESS_WITH_PROMPT": """Document Classification Confirmed.\nDocument Type: **{doc_type}**. The document is now being uploaded for extraction. Please wait 1-2 minutes, then check the retrieval page to see if it has been extracted. If the document is not found, include the filename in your query. You can now ask questions about this document.""",
    
    "CLASSIFICATION_CONFIRMED_FAILURE": """Document Classification Confirmed.\nDocument Type: **{doc_type}**. Failed to upload document. Please try again.""",
    
    "CLASSIFICATION_UPDATED_SUCCESS": """Document Classification Updated.\nDocument Type: **{doc_type}**. The document is now being uploaded for extraction. Please wait 1-2 minutes, then check the retrieval page to see if it has been extracted. If the document is not found, include the filename in your query.""",
    
    "CLASSIFICATION_UPDATED_SUCCESS_WITH_PROMPT": """Document Classification Updated.\nDocument Type: **{doc_type}**. The document is now being uploaded for extraction. Please wait 1-2 minutes, then check the retrieval page to see if it has been extracted. If the document is not found, include the filename in your query. You can now ask questions about this document.""",
    
    "CLASSIFICATION_UPDATED_FAILURE": """Document Classification Updated.\nDocument Type: **{doc_type} (User Selected)**. Failed to upload document. Please try again.""",
    
    "INVALID_DOCUMENT_TYPE": """Invalid document type '{doc_type}'.\nPlease choose from: {document_types}""",
    
    "CLASSIFICATION_NOT_CONFIRMED": """Classification Not Confirmed.\nPlease specify the correct type from: {document_types}""",
    
    "CLASSIFICATION_RESULTS": """Document Classification Results:\n**Document Type:** {doc_type}\nIs this the correct document type? If yes, respond with "Yes", otherwise specify the correct type from: {document_types}"""
}

# Fallback Response Templates
FALLBACK_TEMPLATES = {
    "NO_RESULTS": """I am unable to answer your question due to insufficient data. No matching records were found in the database. Please try rephrasing your query or provide more specific details about what you're looking for.""",
    
    "DOCUMENT_NOT_FOUND": """I am unable to answer your question due to the document not being found. Please verify the document key or upload the document again.""",
    
    "INVOICE_NOT_FOUND": """I am sorry I cannot find any invoice records based on your request. Can you please provide additional details about the invoice you're searching for.""",
    
    "LOAN_NOT_FOUND": """I am sorry, I cannot find any loan records based on your request. Can you please provide more specific information about the loan you're interested in.""",
    
    "BANK_STATEMENT_NOT_FOUND": """I apologize, I cannot find any bank statement records based on your request. Can you please provide additional information like bank name, account number or date range and try again.""",
    
    "SENSITIVE_QUERY": """We have detected that you are trying to ask for sensitive data. We understand your curiosity, but this is sensitive information which we cannot share. If you have other questions related to document processing, classification, or retrieving information from your documents, I'd be happy to help with those.""",
    
    "GENERAL": """I am unable to answer your question at this time. If you have any specific questions about your documents or if you need different information, please let me know."""
} 