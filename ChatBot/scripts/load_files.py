import os
import glob
import json
import time

from chatPackages.loggerConfig import LoggerManager as lg
from chatPackages.dbConnect import DBConnection as db
from chatPackages.nosqlConnection import NoSQLConnectionManager as cm
from chatPackages.pdfStringExtract import PDFUtils as pdfu


def sales_content_preparation(conn, logger):
    from chatPackages.chatBot import SalesChatBot, PDFProcessingService

    google_key_config_path = 'configuration/Google_Key(WinfoBots).json'
    product = 'WinfoTest'

    folder_path = "DownloadedFiles/need to process/pre process"
    for l_file_path in glob.glob(os.path.join(folder_path, "*")):
        PDFProcessingService.upload_pdf_to_gcs(l_file_path, 'SalesDocs', logger, pdf_chuck_size=3,
                                               google_key_path=google_key_config_path, bucket_name='winfobots',
                                               download_path='DownloadedFiles')

    with conn.cursor() as l_db_cursor:
        SalesChatBot.ContentPreparationService.content_preparation(
            bucket_name='winfobots',
            gcs_folder_path='SalesDocs',
            product=product,
            db_cursor=l_db_cursor,
            logger=logger,
            google_key_config_path=google_key_config_path
        )

    SalesChatBot.QuestionService.store_questions_db(product, conn, logger,
                                                    google_key_config_path=google_key_config_path)

    SalesChatBot.EmbeddingService.store_question_embedding_db(conn, logger,
                                                              google_key_config_path=google_key_config_path)

def winfobots_support_content_preparation(nosql_conn, app_conn, logger):
    from chatPackages.chatBot import WinfoBotsSupportProcessFiles

    google_key_config_path = 'configuration/Google_Key(WAI).json'
    product = 'WinfoBots'
    model_name='gemini-2.0-flash-001'
    customer_name = 'Nufarm'
    process_details = {
  "4.5.1 PERFORM ACCOUNTS PAYABLE INVOICING.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "4.5.1 PERFORM ACCOUNTS PAYABLE INVOICING"
  },
  "Accounts Payables Trial Balance.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Accounts Payables Trial Balance"
  },
  "Accrual Reconciliation Load Run.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Accrual Reconciliation Load Run"
  },
  "Actual Cost Process.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Actual Cost Process"
  },
  "Aging - 7 Buckets - By Account - Multi-Fund Accounts Receivable.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Aging - 7 Buckets - By Account - Multi-Fund Accounts Receivable"
  },
  "AP and PO Accrual Reconciliation Report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "AP and PO Accrual Reconciliation Report"
  },
  "AP Invoice Creation - Limitations, Known Issues, and Assumptions.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "AP Invoice Creation - Limitations, Known Issues, and Assumptions"
  },
  "AP Invoice Creation PDD.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "AP Invoice Creation PDD"
  },
  "AP Reconciliation Report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "AP Reconciliation Report"
  },
  "Ap Supplier Invoice Creation FAQ.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "Ap Supplier Invoice Creation FAQ"
  },
  "AP Supplier Invoice Creation User Guide.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "AP Supplier Invoice Creation User Guide"
  },
  "AR Invoice creation PDD.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "AR Invoice creation PDD"
  },
  "AR Invoice Creation User Guide.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "AR Invoice Creation User Guide"
  },
  "AR Invoice PDD.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "AR Invoice PDD"
  },
  "AR Reconciliation Process.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "AR Reconciliation Process"
  },
  "AR Template Steps.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "AR Template Steps"
  },
  "AR_Invoice_WinfoBots_FAQs.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "AR_Invoice_WinfoBots_FAQs"
  },
  "AR_Invoice_WinfoBots_Limitations_KnownIssues_Assumptions.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "AR_Invoice_WinfoBots_Limitations_KnownIssues_Assumptions"
  },
  "As-Is Data Entry- Address Update.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Entry- Address Update"
  },
  "As-Is Data Entry- Extend External.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Entry- Extend External"
  },
  "As-Is Data Entry- Extend Interco.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Entry- Extend Interco"
  },
  "As-Is Data Entry- In-Active Supplier and Sites.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Entry- In-Active Supplier and Sites"
  },
  "As-Is Data Entry- Re-Active Supplier and Sites.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Entry- Re-Active Supplier and Sites"
  },
  "As-Is Data Entry- Self Billing.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Entry- Self Billing"
  },
  "As-Is Data Entry- Supplier Creation as Employee Nufarm.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Entry- Supplier Creation as Employee Nufarm"
  },
  "As-Is Data Entry- Supplier Creation.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Entry- Supplier Creation"
  },
  "As-Is Data Entry- Update Bank Account Supplier Creation.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Entry- Update Bank Account Supplier Creation"
  },
  "As-Is Data Entry- Update Site.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Entry- Update Site"
  },
  "As-Is Data Extraction- Inactivate Supplier.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Extraction- Inactivate Supplier"
  },
  "As-Is Data Extraction- Self Billing.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Extraction- Self Billing"
  },
  "As-Is Data Extraction- Supplier Creation as Employee.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Extraction- Supplier Creation as Employee"
  },
  "As-Is Data Extraction- Supplier Creation.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Extraction- Supplier Creation"
  },
  "As-Is Data Extraction- Update Bank.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "As-Is Data Extraction- Update Bank"
  },
  "Close Cost Calendar.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Close Cost Calendar"
  },
  "Close Inventory Period.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Close Inventory Period"
  },
  "Close Payables Period.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Close Payables Period"
  },
  "Close Purchasing Period.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Close Purchasing Period"
  },
  "Close Receivables.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Close Receivables"
  },
  "COGS Automation.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "COGS Automation"
  },
  "COGS Order Management.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "COGS Order Management"
  },
  "Complete All Transactions for the Period.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Complete All Transactions for the Period"
  },
  "Complete Multiperiod Accounting.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Complete Multiperiod Accounting"
  },
  "Copy Item Costs.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Copy Item Costs"
  },
  "Cost Update in Final Mode (STD).pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Cost Update in Final Mode (STD)"
  },
  "Country Specific Fields.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "Country Specific Fields"
  },
  "Create Accounting - Cost Management.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Create Accounting - Cost Management"
  },
  "Create Accounting - Receiving.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Create Accounting - Receiving"
  },
  "Create Accounting Assets.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Create Accounting Assets"
  },
  "Create Employee as Customer As-Is Extraction.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Create Employee as Customer As-Is Extraction"
  },
  "Create Employee As Customer.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Create Employee As Customer"
  },
  "Create Update Insurance Amount As-Is Extraction.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Create Update Insurance Amount As-Is Extraction"
  },
  "Creation of External Customer.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Creation of External Customer"
  },
  "Creation Of New Price List As-Is Extraction.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Creation Of New Price List As-Is Extraction"
  },
  "Credit Limit Review As-Is Extraction.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Credit Limit Review As-Is Extraction"
  },
  "Customer - Frequently Asked Questions by User.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Customer - Frequently Asked Questions by User"
  },
  "Customer - Limitations - Known Issues.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Customer  - Limitations - Known Issues"
  },
  "Customer Creation PDD .pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Customer Creation  PDD "
  },
  "Customer Creation Technical Architecture Document.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Customer Creation Technical Architecture Document"
  },
  "Customer Creation UI Path TDD.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Customer Creation UI Path TDD"
  },
  "Customer Management User Guide.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Customer Management User Guide"
  },
  "Daily Rates Upload description actual.pdf": {
    "process_area": "Financials",
    "process_name": "Exchange Rates",
    "sub_process": "Daily Rates Upload description actual"
  },
  "Daily_Fx_Architechture.pdf": {
    "process_area": "Financials",
    "process_name": "Exchange Rates",
    "sub_process": "Daily_Fx_Architechture"
  },
  "Daily_Fx_Rates_TDD_UiPath.pdf": {
    "process_area": "Financials",
    "process_name": "Exchange Rates",
    "sub_process": "Daily_Fx_Rates_TDD_UiPath"
  },
  "Daily_FX_Rates_WinfoBots_Limitations_KnownIssues_Assumptions.pdf": {
    "process_area": "Financials",
    "process_name": "Exchange Rates",
    "sub_process": "Daily_FX_Rates_WinfoBots_Limitations_KnownIssues_Assumptions"
  },
  "Define Source Organization setup.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Define Source Organization setup"
  },
  "Distribute Labor Cost.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Distribute Labor Cost"
  },
  "Exchange Rates Manual As-Is Process.pdf": {
    "process_area": "Financials",
    "process_name": "Exchange Rates",
    "sub_process": "Exchange Rates Manual As-Is Process"
  },
  "Exchange Rates PDD (003) (1).pdf": {
    "process_area": "Financials",
    "process_name": "Exchange Rates",
    "sub_process": "Exchange Rates PDD (003) (1)"
  },
  "Exchange Rates User Guide v1.pdf": {
    "process_area": "Financials",
    "process_name": "Exchange Rates",
    "sub_process": "Exchange Rates User Guide v1"
  },
  "Extend Intercompany (Bill To and Ship To).pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Extend Intercompany (Bill To and Ship To)"
  },
  "Extend Intercompany Customer (Bill To and or Ship To).pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Extend Intercompany Customer (Bill To and or Ship To)"
  },
  "External Customer As Is Analysis.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "External Customer As Is Analysis"
  },
  "FA Close.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "FA Close"
  },
  "FA Depreciation Draft.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "FA Depreciation Draft"
  },
  "FAQ for Exchange rates.pdf": {
    "process_area": "Financials",
    "process_name": "Exchange Rates",
    "sub_process": "FAQ for Exchange rates"
  },
  "Fixed Assets Reconciliation.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Fixed Assets Reconciliation"
  },
  "Frequently Asked Questions by Users.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Frequently Asked Questions by Users"
  },
  "Generate Asset Lines for the range of projects.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Generate Asset Lines for the range of projects"
  },
  "GFM period close process for Process Organization.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "GFM period close process for Process Organization"
  },
  "GFM Recreate Batch Period Layers.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "GFM Recreate Batch Period Layers"
  },
  "GL Period Close.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "GL Period Close"
  },
  "Import FX rates.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Import FX rates"
  },
  "Inactive Customer Account or Site.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Inactive Customer Account or Site"
  },
  "Inactive Customer As-Is Extraction.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Inactive Customer As-Is Extraction"
  },
  "Inventory Draft Reconciliation Report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Inventory Draft Reconciliation Report"
  },
  "Inventory Draft Reconciliation with TB.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Inventory Draft Reconciliation with TB"
  },
  "Invoice Validation.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Invoice Validation"
  },
  "Journal Entry Reserve Ledger Report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Journal Entry Reserve Ledger Report"
  },
  "Journals - Auto Reversal.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Journals - Auto Reversal"
  },
  "Launch Interface Managers.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Launch Interface Managers"
  },
  "Manual Document Printing Pattern.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "Manual Document Printing Pattern"
  },
  "Mass addition.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Mass addition"
  },
  "MEC Automation User Guide.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "MEC Automation User Guide"
  },
  "Miscellaneous Accrual Reconciliation Report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Miscellaneous Accrual Reconciliation Report"
  },
  "Month End Period Close Automation PDD.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Month End Period Close Automation PDD"
  },
  "New Accrual journals are created.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "New Accrual journals are created"
  },
  "New accrual journals received in next period.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "New accrual journals received in next period"
  },
  "New Ship To and or Attachment Request As-Is Extraction.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "New Ship To and or Attachment Request As-Is Extraction"
  },
  "New Ship To and Or Attachment.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "New Ship To and Or Attachment"
  },
  "Non PO Steps.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "Non PO Steps"
  },
  "Nufarm OPM Reconciliation Report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Nufarm OPM Reconciliation Report"
  },
  "Open Next Inventory Period.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Open Next Inventory Period"
  },
  "Open next period for Purchasing.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Open next period for Purchasing"
  },
  "Open Period - PA GL.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Open Period - PA GL"
  },
  "Open Period GL.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Open Period GL"
  },
  "Open Periods for AP.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Open Periods for AP"
  },
  "Open the Costing periods for STD and AVG cost types.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Open the Costing periods for STD and AVG cost types"
  },
  "OPM Accounting Pre Processor.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "OPM Accounting Pre Processor"
  },
  "OPM Accounting Pre-Processor.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "OPM Accounting Pre-Processor"
  },
  "Oracle Apex Ap Supplier Invoice Creation TDD.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "Oracle Apex Ap Supplier Invoice Creation TDD"
  },
  "Oracle Apex Ar Invoice Creation TDD.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "Oracle Apex Ar Invoice Creation TDD"
  },
  "Oracle Apex Customer Creation TDD.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Oracle Apex Customer Creation TDD"
  },
  "Oracle Apex Daily Fx Rates TDD.pdf": {
    "process_area": "Financials",
    "process_name": "Exchange Rates",
    "sub_process": "Oracle Apex Daily Fx Rates TDD"
  },
  "PA Period Close.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "PA Period Close"
  },
  "PA Period Reporting.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "PA Period Reporting"
  },
  "PA Period to Pending Close.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "PA Period to Pending Close"
  },
  "Period Close Assistant TDD_Apex.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Period Close Assistant TDD_Apex"
  },
  "Period Close Technical Architecture Document.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Period Close Technical Architecture Document"
  },
  "Period Close_Frequently Asked Questions by Users.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Period Close_Frequently Asked Questions by Users"
  },
  "Period Close_Limitations Known Issues and Assumptions document.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Period Close_Limitations Known Issues and Assumptions document"
  },
  "PO 2 Way Match Steps.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "PO 2 Way Match Steps"
  },
  "PO 3 Way Match Steps.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "PO 3 Way Match Steps"
  },
  "PRC interface Supplier cost.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "PRC interface Supplier cost"
  },
  "Prepare Open item extract.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Prepare Open item extract"
  },
  "Price List - Add New SKU As-Is Extraction.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price List - Add New SKU As-Is Extraction"
  },
  "Price List - Adding New SKU.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price List - Adding New SKU"
  },
  "Price List - Creation of new pricelist.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price List - Creation of new pricelist"
  },
  "Price List - Header Details Updation.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price List - Header Details Updation"
  },
  "Price List - Updating Line Date As-Is Extraction.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price List - Updating Line Date As-Is Extraction"
  },
  "Price List - Updating Line Date.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price List - Updating Line Date"
  },
  "Price List - Updating Line Price As-Is Extraction.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price List - Updating Line Price As-Is Extraction"
  },
  "Price List - Updating Line Price.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price List - Updating Line Price"
  },
  "Price List Creation and Update PDD Document.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price List Creation and Update PDD Document"
  },
  "Price List Header Details Update As-Is Extraction.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price List Header Details Update As-Is Extraction"
  },
  "Price Management User Guide.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price Management User Guide"
  },
  "Price MDM - Frequently Asked Questions by User.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price MDM - Frequently Asked Questions by User"
  },
  "Price MDM TDD_Apex.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price MDM TDD_Apex"
  },
  "Price_MDM_Limitations_KnownIssues_Assumptions.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Price_MDM_Limitations_KnownIssues_Assumptions"
  },
  "Purchasing Reconciliation Period.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Purchasing Reconciliation Period"
  },
  "Python Technical Document(customer).pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Python Technical Document(customer)"
  },
  "Python Technical Document_AP Invoice TDD.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "Python Technical Document_AP Invoice TDD"
  },
  "Python Technical Document_AR_Invoice_Creation.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "Python Technical Document_AR_Invoice_Creation"
  },
  "Python Technical Document_Price List.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Python Technical Document_Price List"
  },
  "Python Technical Document_Vendor MDM.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "Python Technical Document_Vendor MDM"
  },
  "Reactivate Customer Account Site As-Is Extraction.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Reactivate Customer Account  Site As-Is Extraction"
  },
  "Reactive Customer Account and Site.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Reactive Customer Account and Site"
  },
  "Rebate accruals process.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Rebate accruals process"
  },
  "Receipt Accruals - Period End Process.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Receipt Accruals - Period End Process"
  },
  "Refresh Project Summary Accounts.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Refresh Project Summary Accounts"
  },
  "Run aging -7 Buckets -by Amount report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run aging -7 Buckets -by Amount report"
  },
  "Run Cost collection managers.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run Cost collection managers"
  },
  "Run Cost Update Process for AVG in Final Mode.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run Cost Update Process for AVG in Final Mode"
  },
  "Run Create Accounting for payables.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run Create Accounting for payables"
  },
  "Run Distributions Labor Trx.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run Distributions Labor Trx"
  },
  "Run EXC Transaction Exception Details by GL Period.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run EXC Transaction Exception Details by GL Period"
  },
  "Run EXC Transaction Exception Details by PA Period.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run EXC Transaction Exception Details by PA Period"
  },
  "Run Generate Cost Accounting Project.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run Generate Cost Accounting Project"
  },
  "Run incomplete invoices report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run incomplete invoices report"
  },
  "Run Nufarm invoice aging report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run Nufarm invoice aging report"
  },
  "Run Open Interface Transactions Report for Receivables.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run Open Interface Transactions Report for Receivables"
  },
  "Run Open Interface Transactions Report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run Open Interface Transactions Report"
  },
  "Run PRC Create Accounting Requests.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run PRC Create Accounting Requests"
  },
  "Run PRC Interface Assets to Oracle Assets.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run PRC Interface Assets to Oracle Assets"
  },
  "Run Trail Balance Detail.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run Trail Balance Detail"
  },
  "Run unapplied and unresolved receipts register.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Run unapplied and unresolved receipts register"
  },
  "Standard Cost Rollup.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Standard Cost Rollup"
  },
  "Summary Accrual Reconciliation Report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Summary Accrual Reconciliation Report"
  },
  "Supplier Creation and Updation PDD Template v1.5.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "Supplier Creation and Updation PDD Template v1.5"
  },
  "Supplier Creation User Guide.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "Supplier Creation User Guide"
  },
  "Supplier_MDM_WinfoBots_Limitations_KnownIssues_Assumptions.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "Supplier_MDM_WinfoBots_Limitations_KnownIssues_Assumptions"
  },
  "TDD Period Close Process_Uipath.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "TDD Period Close Process_Uipath"
  },
  "Technical Architecture Document - AP Invoice Creation.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "Technical Architecture Document - AP Invoice Creation"
  },
  "Technical Architecture Document - AR Invoice.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "Technical Architecture Document - AR Invoice"
  },
  "Technical Architecture Document - Price MDM.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "Technical Architecture Document - Price MDM"
  },
  "Technical Architecture Document - Supplier MDM.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "Technical Architecture Document - Supplier MDM"
  },
  "Tieback Asset Lines from Oracle Assets.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Tieback Asset Lines from Oracle Assets"
  },
  "Transfer Journal Entries to GL Update.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Transfer Journal Entries to GL Update"
  },
  "Transfer Journal Entries to GL.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Transfer Journal Entries to GL"
  },
  "Transfer to GL Purchasing.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Transfer to GL Purchasing"
  },
  "Trial Balance for Fixed Assets.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Trial Balance for Fixed Assets"
  },
  "Trial Balance for Receivables.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Trial Balance for Receivables"
  },
  "UiPath Technical Document- AR Creation.pdf": {
    "process_area": "Financials",
    "process_name": "AR Invoice Creation",
    "sub_process": "UiPath Technical Document- AR Creation"
  },
  "UiPath Technical Document_Price List.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Price Maintenance",
    "sub_process": "UiPath Technical Document_Price List"
  },
  "Unaccounted Transactions Report XML.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Unaccounted Transactions Report XML"
  },
  "Unapplied cash solved.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Unapplied cash solved"
  },
  "Uninvoiced Receipts Report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Uninvoiced Receipts Report"
  },
  "Unposted Items Report.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Unposted Items Report"
  },
  "Update Cost process.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Update Cost process"
  },
  "Update Credit Limit.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Update Credit Limit"
  },
  "Update Customer Account or Site.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Update Customer Account or Site"
  },
  "Update Customer Bank Details As-Is Extraction.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Update Customer Bank Details As-Is Extraction"
  },
  "Update Customer Bank Details.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Update Customer Bank Details"
  },
  "Update Insured Amount.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Update Insured Amount"
  },
  "Update Payment Term As-Is Extraction.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Update Payment Term As-Is Extraction"
  },
  "Update Payment Terms.pdf": {
    "process_area": "Financials",
    "process_name": "Customer Management",
    "sub_process": "Update Payment Terms"
  },
  "Update Project Summary Amounts.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Update Project Summary Amounts"
  },
  "Vendor - Frequently Asked Questions by User.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "Vendor - Frequently Asked Questions by User"
  },
  "Vendor MDM Apex TDD.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "Vendor MDM Apex TDD"
  },
  "Vendor MDM TDD_Uipath.pdf": {
    "process_area": "Supply Chain Management",
    "process_name": "Vendor Management",
    "sub_process": "Vendor MDM TDD_Uipath"
  },
  "Verify Inventory Journal status.pdf": {
    "process_area": "Financials",
    "process_name": "Period Close",
    "sub_process": "Verify Inventory Journal status"
  },
  "UiPath Technical Document - AP Invoice 1.pdf": {
    "process_area": "Financials",
    "process_name": "AP Invoice Creation",
    "sub_process": "UiPath Technical Document - AP Invoice 1"
  }
}

    folder_path = "DownloadedFiles/SupportDocs/Nufarm"

    # if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
    #     print(f"The path '{folder_path}' is not a valid directory.")
    #     return

    # for absolute_file_path in glob.glob(os.path.join(folder_path, "*")):
    #     file = os.path.basename(absolute_file_path)
    #     process_area = process_details.get(file).get('process_area')
    #     process_name = process_details.get(file).get('process_name')
    #     sub_process = process_details.get(file).get('sub_process')
        #
        # try:
        #     pdf_chunk_file_paths = pdfu.split_pdf(
        #         absolute_file_path, file_name=file, logger=logger, pdf_chuck_size=3,
        #         download_path='DownloadedFiles/SupportDocs'
        #     )
        # except Exception as e:
        #     logger.error(f"Failed to create chunks for file {file}. \nError: {e}")
        #     pdf_chunk_file_paths = []
        #
        # print(f"pdf_chunk_file_paths: {pdf_chunk_file_paths}")
        # # break
        #
        # for each_file_chunk in pdf_chunk_file_paths:
        #     print(f"each_file_chunk: {each_file_chunk}")
        #     WinfoBotsSupportProcessFiles.ContentPreparationService.llm_content_preparation(
        #         file_path=each_file_chunk,
        #         product_name=product,
        #         process_area=process_area,
        #         process_name=process_name,
        #         sub_process=sub_process,
        #         customer_name=customer_name,
        #         nosql_conn=nosql_conn,
        #         logger=logger,
        #         model_name=model_name,
        #         google_key_config_path=google_key_config_path
        #     )
        #     # break
        #     time.sleep(5)
        # break

    WinfoBotsSupportProcessFiles.QuestionService.store_questions_db(
        nosql_conn, app_conn, logger, google_key_config_path=google_key_config_path
    )

    WinfoBotsSupportProcessFiles.EmbeddingService.store_question_embedding_db(
        app_conn, logger, google_key_config_path=google_key_config_path
    )


def oracle_support_content_preparation(nosql_conn, app_conn, logger):
    from chatPackages.chatBot import OracleSupportProcessFiles

    google_key_config_path = 'configuration/Google_Key(WAI).json'
    product = 'Oracle'
    model_name='gemini-2.0-flash-001'
    location='us-central1'
    customer_name = 'WellFul'
    folder_path = "DownloadedFiles/SupportDocs/Oracle/Oracle(WellFul)"

    files_process_details = {
      "SOP for Requisitions.pdf": {
        "process_area": "Procure to Pay",
        "process_name": "Requisition",
        "sub_process": "SOP for Requisitions"
      },
      "SOP - Fixed Price Services PO with Receipt and Invoice.pdf": {
        "process_area": "Procure to Pay",
        "process_name": "Purchase Order Creation",
        "sub_process": "SOP - Fixed Price Services PO with Receipt and Invoice"
      },
      "SOP - Update scheduled ship date.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Receive order",
        "sub_process": "SOP - Update scheduled ship date"
      },
      "SOP - Sales order returns.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Receive order",
        "sub_process": "SOP - Sales order returns"
      },
      "SOP - Release Hold on Sales Order.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Receive order",
        "sub_process": "SOP - Release Hold on Sales Order"
      },
      "SOP - Manual Order Creation.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Receive order",
        "sub_process": "SOP - Manual Order Creation"
      },
      "Sales Order Creation (Requested Date) SOP.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Receive order",
        "sub_process": "Sales Order Creation (Requested Date) SOP"
      },
      "How to release the Pause on SO lines.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Receive order",
        "sub_process": "How to release the Pause on SO lines"
      },
      "DS-140_DESIGN_SPECIFICATION_EDI_850_POI_V3.4.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Receive order",
        "sub_process": "DS-140_DESIGN_SPECIFICATION_EDI_850_POI_V3.4"
      },
      "EDI 940 Cloud_Process_New_V2 - Unit Test Cases.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Ship Request will be sent to WMS",
        "sub_process": "EDI 940 Cloud_Process_New_V2 - Unit Test Cases"
      },
      "EDI 940 Cloud_Process_New_V2 Integration Specification (2).pdf": {
        "process_area": "Order to Cash",
        "process_name": "Ship Request will be sent to WMS",
        "sub_process": "EDI 940 Cloud_Process_New_V2 Integration Specification (2)"
      },
      "EDI 940 Cloud_Process_New_v2 - Mapping Document.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Ship Request will be sent to WMS",
        "sub_process": "EDI 940 Cloud_Process_New_v2 - Mapping Document"
      },
      "DS-140_DESIGN_SPECIFICATION_EDI_945V2.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Ship confimation from WMS",
        "sub_process": "DS-140_DESIGN_SPECIFICATION_EDI_945V2"
      },
      "850_945_856_EDI Errors and Fixes.pdf": {
        "process_area": "Order to Cash",
        "process_name": "Ship confimation from WMS",
        "sub_process": "850_945_856_EDI Errors and Fixes"
      },
      "Transfer Order Bulk Upload Job Aid.pdf": {
        "process_area": "Inventory",
        "process_name": "Transfer Orders",
        "sub_process": "Transfer Order Bulk Upload Job Aid"
      },
      "Transer Order between WMS and Oracle_ Process Flows.pdf": {
        "process_area": "Inventory",
        "process_name": "Transfer Orders",
        "sub_process": "Transer Order between WMS and Oracle_ Process Flows"
      },
      "Amazon Transfer Order Upload Job Aid.pdf": {
        "process_area": "Inventory",
        "process_name": "Transfer Orders",
        "sub_process": "Amazon Transfer Order Upload Job Aid"
      },
      "SOP-Partial shipment of Transfer Order.pdf": {
        "process_area": "Inventory",
        "process_name": "Transfer Orders",
        "sub_process": "SOP-Partial shipment of Transfer Order"
      },
    "Wellful - Procurement Design DocumentV2 - signed.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "Wellful - Procurement Design DocumentV2 - signed"
    },
    "IN-SCM-107-OUT - Receipt Advice_VFinal (1).pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "IN-SCM-107-OUT - Receipt Advice_VFinal (1)"
    },
    "IN-SCM-107-OUT Receipt Advice Integration SpecificationV2.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "IN-SCM-107-OUT Receipt Advice Integration SpecificationV2"
    },
    "Steps to add SFTP Delivery Configuration in Oracle.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "Steps to add SFTP Delivery Configuration in Oracle"
    },
    "Steps to Migrate BI Report.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "Steps to Migrate BI Report"
    },
    "Steps to Run BI Publisher Report in Adhoc.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "Steps to Run BI Publisher Report in Adhoc"
    },
    "Steps to Schedule BI Publisher Report.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "Steps to Schedule BI Publisher Report"
    },
    "IN-SCM-108-IN - Receipt Confirmation_VFinal.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "IN-SCM-108-IN - Receipt Confirmation_VFinal"
    },
    "IN-SCM-108-IN Receipt Confirmation Integration SpecificationV1.2.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "IN-SCM-108-IN Receipt Confirmation Integration SpecificationV1.2"
    },
    "Steps to Migrate Integration in OIC.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "Steps to Migrate Integration in OIC"
    },
    "Steps to Schedule Integration from OIC.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "Steps to Schedule Integration from OIC"
    },
    "Steps to Run OIC Integration Adhoc.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "Steps to Run OIC Integration Adhoc"
    },
    "PO Scenarios.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "PO Scenarios"
    },
    "IN-SCM-108-IN - Receipt Confirmation Tested Scenarios.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "IN-SCM-108-IN - Receipt Confirmation Tested Scenarios"
    },
    "Receipt Confirmation Errors - Receive Manually (1).pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "Receipt Confirmation Errors - Receive Manually (1)"
    },
    "ManageReceivingTransactionsReport_You must enter the quantity.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "ManageReceivingTransactionsReport_You must enter the quantity"
    },
    "ManageReceivingTransactionsReport_The transaction quantity less.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "ManageReceivingTransactionsReport_The transaction quantity less"
    },
    "ManageReceivingTransactionsReport_quantity that's more than 0.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "ManageReceivingTransactionsReport_quantity that's more than 0"
    },
    "ManageReceivingTransactionsReport_PO_LINE_NUM.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "ManageReceivingTransactionsReport_PO_LINE_NUM"
    },
    "ManageReceivingTransactionsReport_PO_HEADER_NUM.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "ManageReceivingTransactionsReport_PO_HEADER_NUM"
    },
    "ManageReceivingTransactionsReport_LOT not matching.pdf": {
      "process_area": "Procure to Pay",
      "process_name": "",
      "sub_process": "ManageReceivingTransactionsReport_LOT not matching"
    },
    "Wellful B2B Order Management Application Design Document 10202022 - signed.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "Wellful B2B Order Management Application Design Document 10202022 - signed"
    },
    "Wellful Shipment Request Integration FDD.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "Wellful Shipment Request Integration FDD"
    },
    "IN-SCM-104-OUT Shipment TO Request to Warehouse Outbound Integration Specificationv2.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "IN-SCM-104-OUT Shipment TO Request to Warehouse Outbound Integration Specificationv2"
    },
    "IN-SCM-104-OUT Shipment TO Request to Warehouse - Steps to Run BI Publisher Report in Adhoc.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "IN-SCM-104-OUT Shipment TO Request to Warehouse - Steps to Run BI Publisher Report in Adhoc"
    },
    "IN-SCM-104-OUT Shipment TO Request to Warehouse - Steps to Migrate BI Report.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "IN-SCM-104-OUT Shipment TO Request to Warehouse - Steps to Migrate BI Report"
    },
    "IN-SCM-104-OUT Shipment TO Request to Warehouse - Steps to add SFTP Delivery Configuration in Oracle.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "IN-SCM-104-OUT Shipment TO Request to Warehouse - Steps to add SFTP Delivery Configuration in Oracle"
    },
    "IN-SCM-104-OUT Shipment TO Request to Warehouse - Steps to Schedule BI Publisher Report.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "IN-SCM-104-OUT Shipment TO Request to Warehouse - Steps to Schedule BI Publisher Report"
    },
    "Wellful Shipment Confirmation Integration Document 08222022 (1).pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "Wellful Shipment Confirmation Integration Document 08222022 (1)"
    },
    "IN-SCM-105-INOUT Shipment Confirmation Integration Specification V3.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "IN-SCM-105-INOUT  Shipment Confirmation Integration Specification V3"
    },
    "IN-SCM-105-INOUT Shipment Confirmation - Test Results.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "IN-SCM-105-INOUT Shipment Confirmation - Test Results"
    },
    "IN-SCM-105-INOUT Shipment Confirmation - Steps to Migrate BI Report.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "IN-SCM-105-INOUT  Shipment Confirmation - Steps to Migrate BI Report"
    },
    "IN-SCM-105-INOUT Shipment Confirmation - Steps to Schedule Integration from OIC.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "IN-SCM-105-INOUT  Shipment Confirmation - Steps to Schedule Integration from OIC"
    },
    "IN-SCM-105-INOUT Shipment Confirmation - Steps to Run OIC Integration Adhoc.pdf": {
      "process_area": "Order to Cash",
      "process_name": "",
      "sub_process": "IN-SCM-105-INOUT  Shipment Confirmation - Steps to Run OIC Integration Adhoc"
    },
    "AN-100_ANALYSIS_SPECIFICATION_EDI_856v2.1 (1).pdf": {
      "process_area": "Order to Cash",
      "process_name": "Send ASN to customer",
      "sub_process": "AN-100_ANALYSIS_SPECIFICATION_EDI_856v2.1 (1)"
    },
    "DS-140_DESIGN_SPECIFICATION_EDI_856v1.0 (1).pdf": {
      "process_area": "Order to Cash",
      "process_name": "Send ASN to customer",
      "sub_process": "DS-140_DESIGN_SPECIFICATION_EDI_856v1.0 (1)"
    },
    "Wellful - Inventory Design DocumentV2 (2) - signed.pdf": {
      "process_area": "Inventory",
      "process_name": "Send ASN to customer",
      "sub_process": "Wellful - Inventory Design DocumentV2 (2) - signed"
    },
    "Ship Request TO New Requirements (AHAMZ,AHWAL).pdf": {
      "process_area": "Inventory",
      "process_name": "Transfer Orders",
      "sub_process": "Ship Request TO New Requirements (AHAMZ,AHWAL)"
    },
    "B2C Perpetual Inventory and Inventory Adjustments Integration Merge FDD (4).pdf": {
      "process_area": "Inventory",
      "process_name": "InSync - Inv Adj from WMS",
      "sub_process": "B2C Perpetual Inventory and Inventory Adjustments Integration Merge FDD (4)"
    },
    "IN-SCM-112-IN-B2C Perpetual and Inventory Adjustmeny Integration TDD.pdf": {
      "process_area": "Inventory",
      "process_name": "InSync - Inv Adj from WMS",
      "sub_process": "IN-SCM-112-IN-B2C Perpetual and Inventory Adjustmeny Integration TDD"
    },
    "IN-SCM-112-IN B2C Perpetual Inventory Adjustment - Steps to Schedule OIC Integration Guide.pdf": {
      "process_area": "Inventory",
      "process_name": "InSync - Inv Adj from WMS",
      "sub_process": "IN-SCM-112-IN B2C Perpetual Inventory Adjustment - Steps to Schedule OIC Integration Guide"
    },
    "IN-SCM-112-IN B2C Perpetual Inventory Adjustment - Steps to Run OIC Integration Adhoc.pdf": {
      "process_area": "Inventory",
      "process_name": "InSync - Inv Adj from WMS",
      "sub_process": "IN-SCM-112-IN B2C Perpetual Inventory Adjustment - Steps to Run OIC Integration Adhoc"
    },
    "IN-SCM-112-IN B2C Perpetual Inventory Adjustment - Steps to Migrate Integration in OIC.pdf": {
      "process_area": "Inventory",
      "process_name": "InSync - Inv Adj from WMS",
      "sub_process": "IN-SCM-112-IN B2C Perpetual Inventory Adjustment - Steps to Migrate Integration in OIC"
    },
    "Error Resolution Document -INSYNC.pdf": {
      "process_area": "Inventory",
      "process_name": "InSync - Inv Adj from WMS",
      "sub_process": "Error Resolution Document -INSYNC"
    }
}
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        print(f"The path '{folder_path}' is not a valid directory.")
        return

    for absolute_file_path in glob.glob(os.path.join(folder_path, "*")):
        file = os.path.basename(absolute_file_path)
        try:
            # absolute_path = os.path.abspath(os.path.join(root, file))
            print(f"Absolute File Path: {absolute_file_path}, File Name: {file}")
            process_name = files_process_details.get(file).get('process_name')
            process_area = files_process_details.get(file).get('process_area')
            sub_process = files_process_details.get(file).get('sub_process')
            print(f"process_name: {process_name}, \nprocess_area: {process_area}, \nsub_process: {sub_process}")
        except Exception as e:
            logger.error(f"Failed to load the files content for file - {file}. \nError: {e}")
            continue

        OracleSupportProcessFiles.ContentPreparationService.content_preparation(
            absolute_file_path,
            file,
            product,
            process_name,
            process_area,
            sub_process,
            customer_name,
            nosql_conn,
            logger,
            google_key_config_path=google_key_config_path,
            model_name=model_name,
            location=location
        )

    OracleSupportProcessFiles.EmbeddingService.store_content_embedding_db(
        nosql_conn, app_conn, logger, google_key_config_path=google_key_config_path
    )


def oracle_general_content_preparation(nosql_conn, app_conn, logger):
    from chatPackages.chatBot import OracleSupportProcessFiles

    google_key_config_path = 'configuration/Google_Key(WAI).json'
#     product = 'Oracle'
#     model_name='gemini-2.0-flash-001'
#     location='us-central1'
#     folder_path = "DownloadedFiles/SupportDocs/Oracle/Oracle(General)"
#
#     files_process_details = {
#   "Scheduled Processes for SCM.pdf": {
#     "process_area": "Supply Chain Management",
#     "process_name": "",
#     "sub_process": "Scheduled Processes for SCM"
#   }
# }
#     if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
#         print(f"The path '{folder_path}' is not a valid directory.")
#         return
#
#     for absolute_file_path in glob.glob(os.path.join(folder_path, "*")):
#         file = os.path.basename(absolute_file_path)
#         try:
#             # absolute_path = os.path.abspath(os.path.join(root, file))
#             print(f"Absolute File Path: {absolute_file_path}, File Name: {file}")
#             process_name = files_process_details.get(file).get('process_name')
#             process_area = files_process_details.get(file).get('process_area')
#             sub_process = files_process_details.get(file).get('sub_process')
#             print(f"process_name: {process_name}, \nprocess_area: {process_area}, \nsub_process: {sub_process}")
#         except Exception as e:
#             logger.error(f"Failed to load the files content for file - {file}. \nError: {e}")
#             continue
#
#         OracleSupportProcessFiles.ContentPreparationService.general_content_preparation(
#             absolute_file_path,
#             file,
#             product,
#             process_name,
#             process_area,
#             sub_process,
#             nosql_conn,
#             logger,
#             google_key_config_path=google_key_config_path,
#             model_name=model_name,
#             location=location
#         )

    OracleSupportProcessFiles.EmbeddingService.store_general_content_embedding_db(
        nosql_conn, app_conn, logger, google_key_config_path=google_key_config_path
    )


if __name__ == '__main__':
    l_logger = lg.configure_logger('logs/load_files')
    l_config = "configuration/db_config.json"
    pool_name = 'oci_db_load_files'

    with open(l_config, 'rb') as config_data:
        config_data = json.load(config_data)

    l_app_conn_details = config_data['WAI_NONPROD']
    l_app_conn = db.connect_db(pool_name, db_details=l_app_conn_details)

    if config_data['WAI_NoSQL'] and str(config_data['WAI_NoSQL']['DatabaseType']).lower() == 'nosql':
        oci_config_data = config_data['WAI_NoSQL']
    else:
        oci_config_data = None

    l_handler = cm.get_nosql_conn(
        compartment_id=oci_config_data['compartment_id'],
        user_id=oci_config_data['user'],
        fingerprint=oci_config_data['fingerprint'],
        tenant_id=oci_config_data['tenancy'],
        region=oci_config_data['region'],
        private_key_file='../certs/oci_private.pem'
    )

    # sales_content_preparation(l_app_conn, l_logger)
    # oracle_support_content_preparation(l_handler, l_app_conn, l_logger)
    # winfobots_support_content_preparation(l_handler, l_app_conn, l_logger)
    oracle_general_content_preparation(l_handler, l_app_conn, l_logger)

    db.close_connection(l_app_conn, pool_name)
    cm.close_nosql_conn(l_handler)
    lg.shutdown_logger(l_logger)
