const { spawn } = require('child_process')

const express = require('express')
const schedule = require('node-schedule')
const compression = require('compression')

const app = express()
app.use(compression())
app.use(express.json())

app.disable('x-powered-by')

function executePythonProcess() {
  const py = spawn('python', ['./py/init.py'])

  py.stdout.pipe(process.stdout)
  py.stderr.pipe(process.stderr)
  py.on('close', (code) => {
    console.log(`child process exited with code ${code}`)
  })

  console.info('Executing python process...')
}

// Execute when app starts
// executePythonProcess()

// Execute python process on Sundays at 3 AM
schedule.scheduleJob({ hour: 3, minute: 0, dayOfWeek: 0 }, executePythonProcess)

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
  PORT: port = 3000
} = process.env

app.listen(port, () => {
  console.info(`Server running at port ${port}`)
})
