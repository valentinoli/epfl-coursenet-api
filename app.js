require('dotenv').config()

const { spawn } = require('child_process')

const express = require('express')
const schedule = require('node-schedule')
const compression = require('compression')
const sendMail = require('./email')

const { catchErrors } = require('./utils')

const app = express()
app.use(compression())
app.use(express.json())

app.disable('x-powered-by')

async function executePythonProcess() {
  const child = spawn('python', ['./py/init.py'])
  console.info('Executing python process...')

  child.stdout.pipe(process.stdout)

  let err = ''
  for await (const chunk of child.stderr) {
    // collect error messages
    err += chunk
  }

  child.on('close', (code) => {
    console.log(`child process exited with code ${code}`)
  })

  // return error messages to caller
  return err
}

// Execute python process on Sundays at 3 AM
schedule.scheduleJob({ hour: 3, minute: 0, dayOfWeek: 0 }, catchErrors(async() => {
  const err = await executePythonProcess()
  if (err) {
    console.error(err)
    await sendMail(err)
  }
}))

const router = require('./router')
app.use(router)

function notFoundHandler(req, res, next) {
  res.status(404).json({ error: 'Not found' })
}

function errorHandler(err, req, res, next) {
  console.error(err)

  if (res.headersSent) {
    // You must delegate to the default Express error handler,
    // when the headers have already been sent to the client
    return next(err);
  }

  return res.status(500).json({ error: 'Internal server error' })
}

app.use(notFoundHandler)
app.use(errorHandler)

const {
  PORT: port = 5000
} = process.env

app.listen(port, () => {
  console.info(`Server running at port ${port}`)
})
