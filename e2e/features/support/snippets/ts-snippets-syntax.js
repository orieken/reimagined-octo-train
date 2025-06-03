function TypeScriptSnippetSyntax(snippetInterface) {
  this.snippetInterface = snippetInterface;
}

function addParameters(allParameterNames) {
  let prefix = '';
  if (allParameterNames.length > 0) {
    prefix = ', ';
  }
  return prefix + allParameterNames.join(', ');
}

TypeScriptSnippetSyntax.prototype.build = function ({
  comment,
  generatedExpressions,
  functionName,
  stepParameterNames,
}) {
  let functionKeyword = '';
  const functionInterfaceKeywords = {
    generator: `${functionKeyword}*`,
    // eslint-disable-next-line @typescript-eslint/naming-convention
    'async-await': `async ${functionKeyword}`,
    promise: 'async ',
  };

  if (this.snippetInterface) {
    functionKeyword = `${functionKeyword}${functionInterfaceKeywords[this.snippetInterface]}`;
  }

  let implementation = "\n  return 'pending';";

  const definitionChoices = generatedExpressions.map((generatedExpression, index) => {
    const prefix = index === 0 ? '' : '// ';

    const allParameterNames = generatedExpression.parameterNames
      .map((parameterName) => `${parameterName}: any`)
      .concat(stepParameterNames.map((stepParameterName) => `${stepParameterName}: any`));

    return (
      `${prefix}${functionName}('` +
      generatedExpression.source.replace(/'/g, "\\'") +
      "', " +
      functionKeyword +
      'function (this: CustomWorld' +
      addParameters(allParameterNames) +
      ') {\n' +
      '  const { page }: CustomWorld = this;\n\n'
    );
  });

  return definitionChoices.join('') + `  // ${comment}\n  ${implementation}\n});`;
};

// eslint-disable-next-line no-undef
module.exports = TypeScriptSnippetSyntax;
