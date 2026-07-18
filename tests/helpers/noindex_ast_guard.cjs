const fs = require('node:fs')
const path = require('node:path')
const ts = require(path.join(process.cwd(), 'node_modules', 'typescript'))

const mode = process.argv[2]
const source = fs.readFileSync(process.argv[3], 'utf8')
const sourceFile = ts.createSourceFile(
  'noindex-guard.ts',
  source,
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TS,
)
const errors = []

function expect(condition, message) {
  if (!condition) errors.push(message)
}

function unwrap(node) {
  while (node && ts.isParenthesizedExpression(node)) node = node.expression
  return node
}

function propertyNameText(name) {
  if (!name) return null
  if (ts.isIdentifier(name) || ts.isStringLiteral(name)) return name.text
  if (ts.isComputedPropertyName(name) && ts.isStringLiteral(name.expression)) {
    return name.expression.text
  }
  return null
}

function namedProperties(object, name) {
  if (!object || !ts.isObjectLiteralExpression(object)) return []
  return object.properties.filter((property) => propertyNameText(property.name) === name)
}

function objectProperty(object, name, label) {
  const properties = namedProperties(object, name)
  expect(properties.length === 1, `${label} must contain exactly one ${name} property`)
  if (properties.length !== 1) return null

  const property = properties[0]
  expect(ts.isPropertyAssignment(property), `${label}.${name} must be a property assignment`)
  if (!ts.isPropertyAssignment(property)) return null

  const initializer = unwrap(property.initializer)
  expect(
    ts.isObjectLiteralExpression(initializer),
    `${label}.${name} must be an object literal`,
  )
  return ts.isObjectLiteralExpression(initializer) ? initializer : null
}

function propertyAssignment(object, name, label) {
  const properties = namedProperties(object, name)
  expect(properties.length === 1, `${label} must contain exactly one ${name} property`)
  if (properties.length !== 1) return null
  expect(
    ts.isPropertyAssignment(properties[0]),
    `${label}.${name} must be a property assignment`,
  )
  return ts.isPropertyAssignment(properties[0]) ? properties[0] : null
}

function isIdentifier(node, name) {
  node = unwrap(node)
  return Boolean(node && ts.isIdentifier(node) && node.text === name)
}

function isStringLiteral(node, value) {
  node = unwrap(node)
  return Boolean(node && ts.isStringLiteral(node) && node.text === value)
}

function isPropertyAccessPath(node, parts) {
  node = unwrap(node)
  for (let index = parts.length - 1; index > 0; index -= 1) {
    if (!ts.isPropertyAccessExpression(node) || node.name.text !== parts[index]) {
      return false
    }
    node = unwrap(node.expression)
  }
  return isIdentifier(node, parts[0])
}

function defaultCall(name) {
  const calls = sourceFile.statements
    .filter((statement) => ts.isExportAssignment(statement) && !statement.isExportEquals)
    .map((statement) => unwrap(statement.expression))
    .filter(
      (expression) =>
        ts.isCallExpression(expression) && isIdentifier(expression.expression, name),
    )

  expect(calls.length === 1, `source must export default exactly one ${name}(...) call`)
  return calls.length === 1 ? calls[0] : null
}

function nuxtConfigObject() {
  const call = defaultCall('defineNuxtConfig')
  if (!call) return null
  expect(call.arguments.length === 1, 'defineNuxtConfig must receive exactly one argument')
  if (call.arguments.length !== 1) return null

  const config = unwrap(call.arguments[0])
  expect(ts.isObjectLiteralExpression(config), 'defineNuxtConfig argument must be an object literal')
  return ts.isObjectLiteralExpression(config) ? config : null
}

function exactSiteNoindexInitializer(initializer) {
  const expression = unwrap(initializer)
  return Boolean(
    expression &&
      ts.isBinaryExpression(expression) &&
      expression.operatorToken.kind === ts.SyntaxKind.ExclamationEqualsEqualsToken &&
      isPropertyAccessPath(expression.left, [
        'process',
        'env',
        'NUXT_PUBLIC_SITE_NOINDEX',
      ]) &&
      isStringLiteral(expression.right, 'false'),
  )
}

function validateRuntimeConfig() {
  const declarations = []
  for (const statement of sourceFile.statements) {
    if (
      !ts.isVariableStatement(statement) ||
      !(statement.declarationList.flags & ts.NodeFlags.Const)
    ) {
      continue
    }
    for (const declaration of statement.declarationList.declarations) {
      if (ts.isIdentifier(declaration.name) && declaration.name.text === 'siteNoindex') {
        declarations.push(declaration)
      }
    }
  }

  expect(
    declarations.length === 1,
    'source must declare exactly one top-level const siteNoindex',
  )
  if (declarations.length === 1) {
    expect(
      exactSiteNoindexInitializer(declarations[0].initializer),
      "siteNoindex initializer must be exactly process.env.NUXT_PUBLIC_SITE_NOINDEX !== 'false'",
    )
  }

  const config = nuxtConfigObject()
  if (!config) return
  const runtimeConfig = objectProperty(config, 'runtimeConfig', 'Nuxt config')
  const publicConfig = objectProperty(runtimeConfig, 'public', 'runtimeConfig')
  if (!publicConfig) return

  const siteNoindexProperties = namedProperties(publicConfig, 'siteNoindex')
  expect(
    siteNoindexProperties.length === 1 &&
      ts.isShorthandPropertyAssignment(siteNoindexProperties[0]),
    'runtimeConfig.public must contain exactly one siteNoindex shorthand property',
  )
}

function validateRobotsMeta() {
  const config = nuxtConfigObject()
  if (!config) return
  const app = objectProperty(config, 'app', 'Nuxt config')
  const head = objectProperty(app, 'head', 'app')
  const metaProperty = propertyAssignment(head, 'meta', 'app.head')
  if (!metaProperty) return

  const meta = unwrap(metaProperty.initializer)
  expect(ts.isArrayLiteralExpression(meta), 'app.head.meta must be an array literal')
  if (!ts.isArrayLiteralExpression(meta)) return

  const robotsEntries = meta.elements.filter((element) => {
    element = unwrap(element)
    if (!ts.isObjectLiteralExpression(element)) return false
    const names = namedProperties(element, 'name')
    return Boolean(
      names.length === 1 &&
        ts.isPropertyAssignment(names[0]) &&
        isStringLiteral(names[0].initializer, 'robots'),
    )
  })
  expect(robotsEntries.length === 0, 'app.head.meta must not contain a static robots authority')
}

function collectNamedProperties(node, name) {
  const properties = []
  function visit(current) {
    if (current.name && propertyNameText(current.name) === name) properties.push(current)
    ts.forEachChild(current, visit)
  }
  ts.forEachChild(node, visit)
  return properties
}

function exactNoindexHeaderSpread(spread) {
  const expression = unwrap(spread.expression)
  if (!ts.isConditionalExpression(expression)) return false
  if (!isIdentifier(expression.condition, 'siteNoindex')) return false

  const whenTrue = unwrap(expression.whenTrue)
  const whenFalse = unwrap(expression.whenFalse)
  if (!ts.isObjectLiteralExpression(whenTrue) || !ts.isObjectLiteralExpression(whenFalse)) {
    return false
  }
  if (whenFalse.properties.length !== 0 || whenTrue.properties.length !== 1) return false

  const header = whenTrue.properties[0]
  return Boolean(
    ts.isPropertyAssignment(header) &&
      propertyNameText(header.name) === 'X-Robots-Tag' &&
      isStringLiteral(header.initializer, 'noindex, follow'),
  )
}

function validateNitroHeaders() {
  const config = nuxtConfigObject()
  if (!config) return
  const nitro = objectProperty(config, 'nitro', 'Nuxt config')
  const routeRules = objectProperty(nitro, 'routeRules', 'nitro')
  const catchAll = objectProperty(routeRules, '/**', 'nitro.routeRules')
  const headers = objectProperty(catchAll, 'headers', "nitro.routeRules['/**']")
  if (!headers) return

  const headerProperties = collectNamedProperties(headers, 'X-Robots-Tag')
  expect(
    headerProperties.length === 0,
    "nitro.routeRules['/**'].headers must not contain a static X-Robots-Tag property",
  )

  const matchingSpreads = headers.properties.filter(
    (property) => ts.isSpreadAssignment(property) && exactNoindexHeaderSpread(property),
  )
  expect(
    matchingSpreads.length === 0,
    "nitro.routeRules['/**'].headers must not contain the legacy conditional noindex spread",
  )
}

function exactRuntimeNoindexCondition(condition, eventName) {
  condition = unwrap(condition)
  if (
    !ts.isPropertyAccessExpression(condition) ||
    condition.name.text !== 'siteNoindex'
  ) {
    return false
  }
  const publicAccess = unwrap(condition.expression)
  if (
    !ts.isPropertyAccessExpression(publicAccess) ||
    publicAccess.name.text !== 'public'
  ) {
    return false
  }
  const runtimeCall = unwrap(publicAccess.expression)
  return Boolean(
    ts.isCallExpression(runtimeCall) &&
      isIdentifier(runtimeCall.expression, 'useRuntimeConfig') &&
      runtimeCall.arguments.length === 1 &&
      isIdentifier(runtimeCall.arguments[0], eventName),
  )
}

function directExpressionStatementCalls(statement) {
  const statements = ts.isBlock(statement) ? statement.statements : [statement]
  return statements
    .filter((candidate) => ts.isExpressionStatement(candidate))
    .map((candidate) => unwrap(candidate.expression))
    .filter((expression) => ts.isCallExpression(expression))
}

function callExpressionsWithin(node) {
  const calls = []
  function visit(current) {
    if (ts.isCallExpression(current)) calls.push(current)
    ts.forEachChild(current, visit)
  }
  visit(node)
  return calls
}

function isAnyRobotsHeaderCall(call) {
  return Boolean(
    isIdentifier(call.expression, 'setResponseHeader') &&
      call.arguments.length >= 2 &&
      isStringLiteral(call.arguments[1], 'X-Robots-Tag'),
  )
}

function isRobotsHeaderCall(call, eventName) {
  return Boolean(
    isAnyRobotsHeaderCall(call) &&
      isIdentifier(call.arguments[0], eventName),
  )
}

function isExactRobotsHeaderCall(call, eventName) {
  return Boolean(
    isRobotsHeaderCall(call, eventName) &&
      call.arguments.length === 3 &&
      isStringLiteral(call.arguments[2], 'noindex, follow'),
  )
}

function validateMiddleware() {
  const call = defaultCall('defineEventHandler')
  if (!call) return
  expect(call.arguments.length === 1, 'defineEventHandler must receive exactly one handler')
  if (call.arguments.length !== 1) return

  const handler = unwrap(call.arguments[0])
  expect(
    ts.isArrowFunction(handler) || ts.isFunctionExpression(handler),
    'defineEventHandler argument must be a function',
  )
  if (!ts.isArrowFunction(handler) && !ts.isFunctionExpression(handler)) return
  expect(handler.parameters.length === 1, 'noindex middleware must receive exactly one event')
  if (handler.parameters.length !== 1 || !ts.isIdentifier(handler.parameters[0].name)) return
  const eventName = handler.parameters[0].name.text

  expect(ts.isBlock(handler.body), 'noindex middleware handler must use a block body')
  if (!ts.isBlock(handler.body)) return

  const allHeaderCalls = callExpressionsWithin(handler.body).filter((candidate) =>
    isAnyRobotsHeaderCall(candidate),
  )
  expect(
    allHeaderCalls.length === 1,
    'middleware handler must contain exactly one X-Robots-Tag setResponseHeader call',
  )

  const matchingIfStatements = handler.body.statements.filter(
    (statement) =>
      ts.isIfStatement(statement) &&
      exactRuntimeNoindexCondition(statement.expression, eventName),
  )
  expect(
    matchingIfStatements.length === 1,
    'middleware must contain exactly one runtimeConfig.public.siteNoindex if statement',
  )

  if (matchingIfStatements.length === 1) {
    const statement = matchingIfStatements[0]
    expect(!statement.elseStatement, 'noindex middleware if statement must not have an else')
    const guardedCalls = directExpressionStatementCalls(statement.thenStatement).filter(
      (candidate) => isRobotsHeaderCall(candidate, eventName),
    )
    expect(
      guardedCalls.length === 1 &&
        isExactRobotsHeaderCall(guardedCalls[0], eventName) &&
        allHeaderCalls.length === 1 &&
        allHeaderCalls[0] === guardedCalls[0],
      "middleware if body must directly execute setResponseHeader(event, 'X-Robots-Tag', 'noindex, follow') exactly once",
    )
  }
}

function propertyAccessParts(node) {
  const parts = []
  node = unwrap(node)
  while (ts.isPropertyAccessExpression(node)) {
    parts.unshift(node.name.text)
    node = unwrap(node.expression)
  }
  if (!ts.isIdentifier(node)) return null
  parts.unshift(node.text)
  return parts
}

function directCall(statement) {
  if (!ts.isExpressionStatement(statement)) return null
  const expression = unwrap(statement.expression)
  return ts.isCallExpression(expression) ? expression : null
}

function exactFinalizeCall(call, ...arguments_) {
  return Boolean(
    call &&
      isIdentifier(call.expression, 'finalizeLaunchResponse') &&
      call.arguments.length === arguments_.length &&
      call.arguments.every((argument, index) => argument.getText(sourceFile) === arguments_[index]),
  )
}

function validateLaunchResponsePlugin() {
  const finalizers = sourceFile.statements.filter(
    (statement) =>
      ts.isFunctionDeclaration(statement) &&
      statement.name?.text === 'finalizeLaunchResponse' &&
      statement.modifiers?.some((modifier) => modifier.kind === ts.SyntaxKind.ExportKeyword),
  )
  expect(
    finalizers.length === 1,
    'source must export exactly one finalizeLaunchResponse function',
  )

  if (finalizers.length === 1) {
    const finalizer = finalizers[0]
    expect(
      finalizer.parameters.length === 2 &&
        ts.isIdentifier(finalizer.parameters[0].name) &&
        finalizer.parameters[0].name.text === 'event' &&
        ts.isIdentifier(finalizer.parameters[1].name) &&
        finalizer.parameters[1].name.text === 'response' &&
        Boolean(finalizer.parameters[1].questionToken),
      'finalizeLaunchResponse must receive event and an optional response body parameter',
    )
    expect(Boolean(finalizer.body), 'finalizeLaunchResponse must have a function body')

    const allRobotsCalls = callExpressionsWithin(sourceFile).filter(isAnyRobotsHeaderCall)
    expect(
      allRobotsCalls.length === 0,
      'launch response plugin must delegate all X-Robots-Tag writes to launchHeaders',
    )
  }

  const pluginCall = defaultCall('defineNitroPlugin')
  if (!pluginCall) return
  expect(pluginCall.arguments.length === 1, 'defineNitroPlugin must receive exactly one handler')
  if (pluginCall.arguments.length !== 1) return

  const handler = unwrap(pluginCall.arguments[0])
  expect(
    ts.isArrowFunction(handler) || ts.isFunctionExpression(handler),
    'defineNitroPlugin argument must be a function',
  )
  if (!ts.isArrowFunction(handler) && !ts.isFunctionExpression(handler)) return
  expect(
    handler.parameters.length === 1 &&
      ts.isIdentifier(handler.parameters[0].name) &&
      handler.parameters[0].name.text === 'nitroApp',
    'launch response plugin must receive exactly one nitroApp parameter',
  )
  expect(ts.isBlock(handler.body), 'launch response plugin handler must use a block body')
  if (!ts.isBlock(handler.body)) return

  const hookCalls = handler.body.statements
    .map(directCall)
    .filter((call) => {
      if (!call) return false
      const parts = propertyAccessParts(call.expression)
      return parts?.join('.') === 'nitroApp.hooks.hook'
    })
  expect(
    hookCalls.length === 2,
    'launch response plugin must register exactly beforeResponse and error hooks',
  )

  const namedHooks = new Map()
  for (const call of hookCalls) {
    if (!call || call.arguments.length !== 2 || !ts.isStringLiteral(call.arguments[0])) continue
    const name = call.arguments[0].text
    namedHooks.set(name, [...(namedHooks.get(name) || []), call])
  }
  expect(
    namedHooks.get('beforeResponse')?.length === 1,
    'launch response plugin must register exactly one beforeResponse hook',
  )
  expect(
    namedHooks.get('error')?.length === 1,
    'launch response plugin must register exactly one error hook',
  )

  const beforeCall = namedHooks.get('beforeResponse')?.[0]
  const beforeHandler = beforeCall && unwrap(beforeCall.arguments[1])
  if (beforeHandler) {
    expect(
      ts.isArrowFunction(beforeHandler) &&
        beforeHandler.parameters.length === 2 &&
        ts.isIdentifier(beforeHandler.parameters[0].name) &&
        beforeHandler.parameters[0].name.text === 'event' &&
        ts.isIdentifier(beforeHandler.parameters[1].name) &&
        beforeHandler.parameters[1].name.text === 'response' &&
        ts.isBlock(beforeHandler.body) &&
        beforeHandler.body.statements.length === 1 &&
        exactFinalizeCall(directCall(beforeHandler.body.statements[0]), 'event', 'response'),
      'beforeResponse hook must directly finalize the current event and response body',
    )
  }

  const errorCall = namedHooks.get('error')?.[0]
  const errorHandler = errorCall && unwrap(errorCall.arguments[1])
  if (errorHandler) {
    let validErrorHook = false
    if (
      ts.isArrowFunction(errorHandler) &&
      errorHandler.parameters.length === 2 &&
      ts.isIdentifier(errorHandler.parameters[1].name) &&
      errorHandler.parameters[1].name.text === 'context' &&
      ts.isBlock(errorHandler.body) &&
      errorHandler.body.statements.length === 1
    ) {
      const statement = errorHandler.body.statements[0]
      if (
        ts.isIfStatement(statement) &&
        !statement.elseStatement &&
        propertyAccessParts(statement.expression)?.join('.') === 'context.event'
      ) {
        const calls = directExpressionStatementCalls(statement.thenStatement)
        validErrorHook = calls.length === 1 && exactFinalizeCall(calls[0], 'context.event')
      }
    }
    expect(validErrorHook, 'error hook must synchronously finalize context.event when present')
  }
}

if (sourceFile.parseDiagnostics.length > 0) {
  for (const diagnostic of sourceFile.parseDiagnostics) {
    errors.push(ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n'))
  }
} else if (mode === 'runtime') {
  validateRuntimeConfig()
} else if (mode === 'nitro') {
  validateNitroHeaders()
} else if (mode === 'config') {
  validateRuntimeConfig()
  validateRobotsMeta()
  validateNitroHeaders()
} else if (mode === 'middleware') {
  validateMiddleware()
} else if (mode === 'plugin') {
  validateLaunchResponsePlugin()
} else {
  errors.push(`unknown guard mode: ${mode}`)
}

if (errors.length > 0) {
  process.stderr.write(`${errors.join('\n')}\n`)
  process.exit(1)
}
