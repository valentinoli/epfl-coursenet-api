const nodemailer = require('nodemailer')

async function sendMail(text) {
  // create reusable transporter object using the default SMTP transport
  const transporter = nodemailer.createTransport({
    host: 'smtp.gmail.com',
    port: 465,
    secure: true,
    auth: {
      type: 'OAuth2',
      user: 'valentin.loftsson@gmail.com',
      clientId: process.env.OAUTH2_CLIENT_ID,
      clientSecret: process.env.OAUTH2_CLIENT_SECRET,
      refreshToken: process.env.OAUTH2_REFRESH_TOKEN
    },
  })

  // send mail with defined transport object
  const info = await transporter.sendMail({
    from: 'valentin.loftsson@gmail.com', // sender address
    to: 'valentin.loftsson@gmail.com', // list of receivers
    subject: '[ERROR] EPFL CourseNet', // Subject line
    text, // plain text body
  })

  console.log('Message sent: %s', info.messageId)
  // Message sent: <b658f8ca-6296-ccf4-8306-87d57a0b4321@example.com>

  // Preview only available when sending through an Ethereal account
  console.log('Preview URL: %s', nodemailer.getTestMessageUrl(info))
  // Preview URL: https://ethereal.email/message/WaQKMgKddxQDoou...
}

module.exports = sendMail
