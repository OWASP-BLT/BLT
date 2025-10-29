import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authService } from '../services/auth';

const Register = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password1: '',
    password2: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    // Clear error for this field when user starts typing
    if (errors[e.target.name]) {
      setErrors({ ...errors, [e.target.name]: '' });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrors({});
    setLoading(true);

    try {
      await authService.register(formData);
      navigate('/dashboard');
    } catch (err) {
      setErrors(err);
    } finally {
      setLoading(false);
    }
  };

  const getErrorMessage = (field) => {
    const error = errors[field];
    if (Array.isArray(error)) {
      return error[0];
    }
    return error;
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-gray-2">
      <div className="max-w-md w-full bg-white rounded-lg shadow-card p-8">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold mb-2">Create Account</h2>
          <p className="text-body">Join the BLT community</p>
        </div>

        {errors.non_field_errors && (
          <div className="mb-4 p-3 error-message border rounded-lg">
            <p className="text-sm">{getErrorMessage('non_field_errors')}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="username" className="block text-sm font-medium mb-2">
              Username
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              className={`w-full px-4 py-2 border rounded-lg input-focus transition-shadow ${
                errors.username ? 'border-danger' : 'border-stroke'
              }`}
            />
            {errors.username && (
              <p className="mt-1 text-sm error-message">{getErrorMessage('username')}</p>
            )}
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-2">
              Email
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              className={`w-full px-4 py-2 border rounded-lg input-focus transition-shadow ${
                errors.email ? 'border-danger' : 'border-stroke'
              }`}
            />
            {errors.email && (
              <p className="mt-1 text-sm error-message">{getErrorMessage('email')}</p>
            )}
          </div>

          <div>
            <label htmlFor="password1" className="block text-sm font-medium mb-2">
              Password
            </label>
            <input
              type="password"
              id="password1"
              name="password1"
              value={formData.password1}
              onChange={handleChange}
              required
              className={`w-full px-4 py-2 border rounded-lg input-focus transition-shadow ${
                errors.password1 ? 'border-danger' : 'border-stroke'
              }`}
            />
            {errors.password1 && (
              <p className="mt-1 text-sm error-message">{getErrorMessage('password1')}</p>
            )}
          </div>

          <div>
            <label htmlFor="password2" className="block text-sm font-medium mb-2">
              Confirm Password
            </label>
            <input
              type="password"
              id="password2"
              name="password2"
              value={formData.password2}
              onChange={handleChange}
              required
              className={`w-full px-4 py-2 border rounded-lg input-focus transition-shadow ${
                errors.password2 ? 'border-danger' : 'border-stroke'
              }`}
            />
            {errors.password2 && (
              <p className="mt-1 text-sm error-message">{getErrorMessage('password2')}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg btn-primary font-semibold transition-colors disabled:opacity-50"
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-body">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold hover:underline" style={{ color: '#e74c3c' }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
