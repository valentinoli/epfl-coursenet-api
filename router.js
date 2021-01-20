const { promisify } = require('util')
const exec = promisify(require('child_process').exec)

const express = require('express')
const redis = require('redis')

const router = express.Router()

const {
  REDIS_URL = 'redis://@localhost:6379'
} = process.env;
const client = redis.createClient({ url: REDIS_URL });

const getAsync = promisify(client.get).bind(client)

const catchErrors = (fn) => {
  return (req, res, next) => fn(req, res, next).catch(next)
}

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
  const cmd = `py ./py/search/query.py ${topk} ${query}`
  const { stdout, stderr } = await exec(cmd)

  console.log('stdout:', stdout)
  console.error('stderr:', stderr)

  if (stderr) {
    return res.status(500).json({ error: stderr })
  }

  return res.json(JSON.parse(stdout))
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
    }
  })
})
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

module.exports = router
