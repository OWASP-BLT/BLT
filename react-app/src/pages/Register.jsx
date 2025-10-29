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
          <div className="mb-4 p-3 bg-danger bg-opacity-10 border border-danger rounded-lg" style={{ borderColor: '#e74c3c', backgroundColor: 'rgba(231, 76, 60, 0.1)' }}>
            <p className="text-sm" style={{ color: '#e74c3c' }}>{getErrorMessage('non_field_errors')}</p>
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
              className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 transition-shadow ${
                errors.username ? 'border-danger' : 'border-stroke'
              }`}
              onFocus={(e) => e.target.style.borderColor = '#e74c3c'}
              onBlur={(e) => e.target.style.borderColor = errors.username ? '#e74c3c' : '#E2E8F0'}
            />
            {errors.username && (
              <p className="mt-1 text-sm" style={{ color: '#e74c3c' }}>{getErrorMessage('username')}</p>
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
              className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 transition-shadow ${
                errors.email ? 'border-danger' : 'border-stroke'
              }`}
              onFocus={(e) => e.target.style.borderColor = '#e74c3c'}
              onBlur={(e) => e.target.style.borderColor = errors.email ? '#e74c3c' : '#E2E8F0'}
            />
            {errors.email && (
              <p className="mt-1 text-sm" style={{ color: '#e74c3c' }}>{getErrorMessage('email')}</p>
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
              className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 transition-shadow ${
                errors.password1 ? 'border-danger' : 'border-stroke'
              }`}
              onFocus={(e) => e.target.style.borderColor = '#e74c3c'}
              onBlur={(e) => e.target.style.borderColor = errors.password1 ? '#e74c3c' : '#E2E8F0'}
            />
            {errors.password1 && (
              <p className="mt-1 text-sm" style={{ color: '#e74c3c' }}>{getErrorMessage('password1')}</p>
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
              className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 transition-shadow ${
                errors.password2 ? 'border-danger' : 'border-stroke'
              }`}
              onFocus={(e) => e.target.style.borderColor = '#e74c3c'}
              onBlur={(e) => e.target.style.borderColor = errors.password2 ? '#e74c3c' : '#E2E8F0'}
            />
            {errors.password2 && (
              <p className="mt-1 text-sm" style={{ color: '#e74c3c' }}>{getErrorMessage('password2')}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg text-white font-semibold transition-colors disabled:opacity-50"
            style={{ backgroundColor: '#e74c3c' }}
            onMouseEnter={(e) => !loading && (e.target.style.backgroundColor = '#c0392b')}
            onMouseLeave={(e) => !loading && (e.target.style.backgroundColor = '#e74c3c')}
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
