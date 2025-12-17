"""
Database schema definitions for various document types.
Each schema defines the table structure, fields, and relationships between tables.
These schemas are based on Django model definitions.
"""

INVOICE_DB_TABLE_SCHEMA = {
    "invoice_details": {
        "table": "invoice_details",
        "description": "Stores detailed information about invoice documents",
        "fields": {
            "id": {"type": "INTEGER", "primary_key": True, "description": "Unique identifier for the invoice record"},
            "document_id": {"type": "INTEGER", "null": True, "description": "Reference to parent document (ForeignKey)"},
            "invoice_number": {"type": "VARCHAR(255)", "db_index": True, "description": "Unique invoice number"},
            "invoice_date": {"type": "VARCHAR(255)", "db_index": True, "description": "Date when invoice was issued"},
            "due_date": {"type": "VARCHAR(255)", "db_index": True, "description": "Payment due date"},
            "total_tax": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Total tax amount"},
            "sub_total": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Total before taxes"},
            "grand_total": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Total including taxes"},
            "currency": {"type": "VARCHAR(255)", "db_index": True, "description": "Currency code"},
            "supplier": {"type": "VARCHAR(255)", "db_index": True, "description": "Supplier information"},
            "customer": {"type": "VARCHAR(255)", "db_index": True, "description": "Customer information"},
            "invoice_type": {"type": "VARCHAR(255)", "db_index": True, "description": "Type of invoice"},
            "tax_number": {"type": "VARCHAR(255)", "db_index": True, "description": "Tax identification number"},
            "company_registration_number": {"type": "VARCHAR(255)", "db_index": True, "description": "Company registration number"},
            "token_cost": {"type": "DECIMAL(25,4)", "default": 0.00, "description": "Cost in tokens for processing"},
            "tax_scheme": {"type": "VARCHAR(255)", "db_index": True, "default": "GST", "description": "Tax scheme used"},
            "inc_of_tax": {"type": "BOOLEAN", "default": False, "description": "Whether tax is included"},
            "created_at": {"type": "TIMESTAMP", "auto_now_add": True, "description": "Record creation timestamp"},
            "updated_at": {"type": "TIMESTAMP", "auto_now": True, "description": "Last update timestamp"}
        },
        "relationships": [
            {"from": "document_id", "to": "documents.id", "type": "foreign_key", "on_delete": "CASCADE"}
        ],
        "meta": {
            "db_table": "invoice_details",
            "default_permissions": []
        }
    },
    "documents": {
        "table": "documents",
        "description": "Base table for all document types",
        "fields": {
            "id": {"type": "INTEGER", "primary_key": True, "description": "Unique document identifier"},
            "aws_key": {"type": "VARCHAR(255)", "not_null": True, "description": "S3 storage key"}
        }
    }
}

DOCUMENT_DB_TABLE_SCHEMA = {
    "documents": {
        "table": "documents",
        "description": "Base table for all document types with extended metadata",
        "fields": {
            "id": {"type": "INTEGER", "primary_key": True, "description": "Unique document identifier"},
            "aws_key": {"type": "TEXT", "unique": True, "description": "S3 storage key"},
            "uuid": {"type": "UUID", "unique": True, "null": True, "default": "uuid.uuid4", "description": "Unique identifier for the document"},
            "company_id": {"type": "INTEGER", "null": True, "description": "Reference to company"},
            "aws_response_id": {"type": "INTEGER", "null": True, "description": "Reference to AWS processing response"},
            "updated_at": {"type": "TIMESTAMP", "auto_now": True, "null": True, "description": "Last update timestamp"},
            "created_at": {"type": "TIMESTAMP", "auto_now_add": True, "description": "Creation timestamp"},
            "status": {"type": "TEXT", "default": "open", "description": "Document processing status"},
            "model_name": {"type": "TEXT", "default": "gpt-3.5", "description": "Model used for processing"},
            "message": {"type": "TEXT", "default": "Document submitted for analysis", "description": "Processing message or error"},
            "account_name": {"type": "TEXT", "blank": True, "description": "Account name associated with document"},
            "document_type": {"type": "TEXT", "blank": True, "description": "Type of document"},
            "business_country": {"type": "TEXT", "blank": True, "default": "Singapore", "description": "Country code of business"},
            "number_of_pages": {"type": "INTEGER", "default": 0, "description": "Number of pages in document"},
            "classify": {"type": "BOOLEAN", "default": False, "description": "Whether document needs classification"},
            "progress_percentage": {"type": "INTEGER", "default": 0, "description": "Processing progress percentage"},
            "assignee_id": {"type": "INTEGER", "null": True, "description": "User assigned to document"},
            "assignee_at": {"type": "TIMESTAMP", "null": True, "description": "Assignment timestamp"},
            "resolved_at": {"type": "TIMESTAMP", "null": True, "description": "Resolution timestamp"},
            "last_activity": {"type": "TIMESTAMP", "null": True, "description": "Last activity timestamp"}
        },
        "relationships": [
            {"from": "aws_response_id", "to": "aws_responses.id", "type": "foreign_key", "on_delete": "SET_NULL"},
            {"from": "assignee_id", "to": "users.id", "type": "foreign_key", "on_delete": "SET_NULL"}
        ],
        "meta": {
            "db_table": "documents",
            "default_permissions": []
        }
    },
    "logs": {
        "table": "logs",
        "description": "System logs for document processing",
        "fields": {
            "id": {"type": "INTEGER", "primary_key": True, "description": "Unique log identifier"},
            "timestamp": {"type": "TIMESTAMP", "not_null": True, "description": "Log timestamp"},
            "message": {"type": "TEXT", "not_null": True, "description": "Log message"},
            "level": {"type": "VARCHAR(20)", "not_null": True, "description": "Log level (e.g., INFO, ERROR)"}
        }
    }
}

BANK_STATEMENT_DB_SCHEMA = {
    "bank_statement_details": {
        "table": "bank_statement_details",
        "description": "Stores detailed information about bank statement documents",
        "fields": {
            "id": {"type": "INTEGER", "primary_key": True, "description": "Unique identifier for the bank statement record"},
            "document_id": {"type": "INTEGER", "null": True, "description": "Reference to parent document (OneToOneField)"},
            "bank_name": {"type": "VARCHAR(255)", "db_index": True, "description": "Name of the bank"},
            "matches_valid_bank_name": {"type": "BOOLEAN", "default": False, "description": "Whether bank name matches known banks"},
            "company_name": {"type": "VARCHAR(255)", "db_index": True, "description": "Company name on statement"},
            "account_number": {"type": "VARCHAR(255)", "db_index": True, "description": "Bank account number"},
            "currency": {"type": "VARCHAR(255)", "db_index": True, "description": "Currency code"},
            "opening_balance": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Opening balance"},
            "start_date": {"type": "DATE", "db_index": True, "null": True, "description": "Statement start date"},
            "closing_balance": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Closing balance"},
            "end_date": {"type": "DATE", "db_index": True, "null": True, "description": "Statement end date"},
            "total_debits_count": {"type": "INTEGER", "default": 0, "description": "Total number of debit transactions"},
            "total_debit_amount": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Total amount of debits"},
            "total_credits_count": {"type": "INTEGER", "default": 0, "description": "Total number of credit transactions"},
            "total_credit_amount": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Total amount of credits"},
            "token_cost": {"type": "DECIMAL(25,4)", "default": 0.00, "description": "Cost in tokens for processing"},
            "created_at": {"type": "TIMESTAMP", "auto_now_add": True, "description": "Record creation timestamp"},
            "updated_at": {"type": "TIMESTAMP", "auto_now": True, "description": "Last update timestamp"}
        },
        "relationships": [
            {"from": "document_id", "to": "documents.id", "type": "foreign_key", "on_delete": "CASCADE"}
        ],
        "meta": {
            "db_table": "bank_statement_details",
            "default_permissions": []
        }
    },
    "documents": {
        "table": "documents",
        "description": "Base table for all document types",
        "fields": {
            "id": {"type": "INTEGER", "primary_key": True, "description": "Unique document identifier"},
            "aws_key": {"type": "VARCHAR(255)", "not_null": True, "description": "S3 storage key"},
            "company_id": {"type": "INTEGER", "not_null": True, "description": "Reference to company"}
        }
    }
}

LOAN_DB_TABLE_SCHEMA = {
    "loan_details": {
        "table": "loan_details",
        "description": "Stores detailed information about loan documents",
        "fields": {
            "id": {"type": "INTEGER", "primary_key": True, "description": "Unique identifier for the loan record"},
            "document_id": {"type": "INTEGER", "null": True, "description": "Reference to parent document (OneToOneField)"},
            "account_name": {"type": "VARCHAR(255)", "db_index": True, "description": "Name of the loan account"},
            "account_number": {"type": "VARCHAR(255)", "db_index": True, "description": "Unique account number"},
            "start_date": {"type": "DATE", "db_index": True, "null": True, "description": "Loan start date"},
            "end_date": {"type": "DATE", "db_index": True, "null": True, "description": "Loan end date"},
            "currency": {"type": "VARCHAR(255)", "db_index": True, "description": "Currency code"},
            "principal_amount": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Original loan amount"},
            "fixed_interest_rate": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Fixed interest rate if applicable"},
            "annual_variable_interest": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Annual variable interest rate"},
            "installment_amount": {"type": "DECIMAL(25,2)", "default": 0.00, "description": "Regular payment amount"},
            "token_cost": {"type": "DECIMAL(25,4)", "default": 0.00, "description": "Cost in tokens for processing"},
            "created_at": {"type": "TIMESTAMP", "auto_now_add": True, "description": "Record creation timestamp"},
            "updated_at": {"type": "TIMESTAMP", "auto_now": True, "description": "Last update timestamp"}
        },
        "relationships": [
            {"from": "document_id", "to": "documents.id", "type": "foreign_key", "on_delete": "CASCADE"}
        ],
        "meta": {
            "db_table": "loan_details",
            "default_permissions": []
        }
    },
    "documents": {
        "table": "documents",
        "description": "Base table for all document types",
        "fields": {
            "id": {"type": "INTEGER", "primary_key": True, "description": "Unique document identifier"},
            "aws_key": {"type": "VARCHAR(255)", "not_null": True, "description": "S3 storage key"},
            "company_id": {"type": "INTEGER", "not_null": True, "description": "Reference to company"}
        }
    }
}