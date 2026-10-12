import { loginUrl } from '../api.js'

// Sign-in happens on Django's own CSRF-protected form; the password never touches this React app.
export default function SignIn() {
  return (
    <section className="panel signin" aria-labelledby="signin-heading">
      <h2 id="signin-heading">Sign in required</h2>
      <p className="muted">Use your operator account to manage QuickBooks sandbox connections.</p>
      <a className="button button-primary" href={loginUrl}>
        Sign in
      </a>
    </section>
  )
}
