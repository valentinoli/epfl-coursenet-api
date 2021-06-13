const { promisify } = require('util')
const exec = promisify(require('child_process').exec)
const { spawn } = require('child_process')

const express = require('express')
const redis = require('redis')

const router = express.Router()
router.use(express.json())

const {
  REDIS_URL = 'redis://@localhost:6379'
} = process.env;
const client = redis.createClient({ url: REDIS_URL });

client.on('connect', () => console.log('Redis connected!'))
client.on('error', console.error)

const getAsync = promisify(client.get).bind(client)

const { catchErrors } = require('./utils')

/**
 * Fetches data by key from redis cache
 *
 * @param {string} key - key under which data is stored
 * @returns {Object}
 */
async function fromCache(key) {
  const cached = await getAsync(key)
  return JSON.parse(cached)
}

async function getNavigation(req, res, next) {
  const value = await fromCache('nav')
  if (!value) {
    return next()
  }
  return res.json(value)
}

async function getEPFL(req, res, next) {
  const {
    level = '',
    program = '',
    specialization = ''
  } = req.params

  const redisKey = ['epfl', level, program, specialization].filter(s => s).join('_')
  const value = await fromCache(redisKey)
  if (!value) {
    return next()
  }
  return res.json(value)
}

async function getCourse(req, res, next) {
  const { slug } = req.params
  const redisKey = `course_${slug}`
  const value = await fromCache(redisKey)
  if (!value) {
    return next()
  }
  return res.json(value)
}

async function submitQuery(req, res, next) {
  const { query, topk = 10 } = req.query
  if (!query) {
    return res.status(400).json({ error: 'Parameter <query> is missing' })
  }
  const cmd = `python ./py/search/query.py ${topk} ${query}`
  console.log(query)
  const { stdout, stderr } = await exec(cmd)

  console.log('stdout:', stdout)
  console.error('stderr:', stderr)

  if (stderr) {
    return res.status(500).json({ error: stderr })
  }

  return res.json(JSON.parse(stdout))
}

async function findSimlinks(req, res, next) {
  const { threshold, slugs } = req.body

  // todo improve request body validation?
  if (!Array.isArray(slugs) || !threshold) {
    return res.status(400).json({ error: 'Invalid parameters' })
  }

  const child = spawn('python', ['./py/search/simlinks.py'])
  child.stderr.pipe(process.stderr)

  child.stdin.write(`${threshold}#${slugs}`)
  child.stdin.end()  // important to call end()!

  let data = ''
  for await (const chunk of child.stdout) {
    data += chunk
  }

  return res.json(JSON.parse(data))
}

router.get('/', (req, res) => {
  res.json({
    '/epfl': {
      '/': 'Root of EPFL coursebook tree',
      '/:level': 'Academic level',
      '/:level/:program': 'Study program',
      '/master/:program/:specialization': 'Master specialization'
    },
    '/course': {
      '/:slug': 'Detailed course information',
      '/search?query=<query>&topk=10': 'Keyword search'
    },
    '/nav': 'Treeview navigation structure'
  })
})
router.get(
  '/nav',
  catchErrors(getNavigation)
)
router.get(
  '/epfl/:level([a-z-]+)?/:program([a-z-]+)?/:specialization([a-z-]+)?',
  catchErrors(getEPFL)
)
router.get(
  '/course/:slug([a-z0-9-]+)',
  catchErrors(getCourse)
)
router.get(
  '/course/search',
  catchErrors(submitQuery)
)
router.post(
  '/simlinks',
  catchErrors(findSimlinks)
)

module.exports = router
