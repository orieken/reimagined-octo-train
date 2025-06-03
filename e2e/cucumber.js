const formatOptions = JSON.stringify({
  snippetInterface: 'async-await',
  snippetSyntax: './features/support/snippets/ts-snippets-syntax.js',
});

const timestamp = new Date().toISOString().replace(/[:-]/g, '').replace(/\..+/, '');

const common = `
  --require features/**/*.ts
  --require-module ts-node/register
  --format @cucumber/pretty-formatter
  --format-options ${formatOptions}
  --format html:./reports/cucumber_report-${timestamp}.html
  --format json:./reports/cucumber_report-${timestamp}.json
  `;

// eslint-disable-next-line no-undef
module.exports = {
  default: `${common}`,
};
