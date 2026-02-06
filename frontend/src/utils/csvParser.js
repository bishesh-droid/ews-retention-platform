// frontend/src/utils/csvParser.js

export const parseCSV = (csvString) => {
  const lines = csvString.trim().split('\n');
  if (lines.length === 0) {
    return [];
  }

  const headers = lines[0].split(',').map(header => header.trim());
  const data = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(value => value.trim());
    const row = {};
    headers.forEach((header, index) => {
      // Attempt to convert to number if possible, otherwise keep as string
      row[header] = isNaN(Number(values[index])) ? values[index] : Number(values[index]);
    });
    data.push(row);
  }
  return data;
};
