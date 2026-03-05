function doPost(e) {

  const sheet = SpreadsheetApp.getActiveSpreadsheet()
    .getSheetByName("mexico_migration_status");

  const data = JSON.parse(e.postData.contents);

  sheet.appendRow([
    data.tenant,
    data.status,
    data.timestamp
  ]);

  return ContentService
    .createTextOutput(JSON.stringify({status:"ok"}))
    .setMimeType(ContentService.MimeType.JSON);
}
