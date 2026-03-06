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

function doGet(e) {

  const sheetName = e.parameter.sheet;
  const range = e.parameter.range;

  const sheet = SpreadsheetApp
      .getActiveSpreadsheet()
      .getSheetByName(sheetName);

  const data = sheet.getRange(range).getValues();

  const headers = data[0];

  const rows = data.slice(1).map(r => {
    let obj = {};
    headers.forEach((h,i) => obj[h] = r[i]);
    return obj;
  });

  return ContentService
    .createTextOutput(JSON.stringify(rows))
    .setMimeType(ContentService.MimeType.JSON);
}
