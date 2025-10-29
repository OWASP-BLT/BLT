import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer className="bg-black text-white mt-auto">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* About Section */}
          <div>
            <h3 className="text-xl font-bold mb-4 text-[#e74c3c]">
              OWASP BLT
            </h3>
            <p className="text-bodydark text-sm">
              Bug Logging Tool - Report bugs, earn points, and make the web more secure.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-semibold mb-4">Quick Links</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/issues" className="text-bodydark hover:text-white transition-colors">
                  Browse Issues
                </Link>
              </li>
              <li>
                <Link to="/organizations" className="text-bodydark hover:text-white transition-colors">
                  Organizations
                </Link>
              </li>
              <li>
                <Link to="/leaderboard" className="text-bodydark hover:text-white transition-colors">
                  Leaderboard
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="font-semibold mb-4">Resources</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="https://github.com/OWASP-BLT/BLT"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-bodydark hover:text-white transition-colors"
                >
                  GitHub
                </a>
              </li>
              <li>
                <Link to="/about" className="text-bodydark hover:text-white transition-colors">
                  About
                </Link>
              </li>
              <li>
                <Link to="/terms" className="text-bodydark hover:text-white transition-colors">
                  Terms of Service
                </Link>
              </li>
              <li>
                <Link to="/privacy" className="text-bodydark hover:text-white transition-colors">
                  Privacy Policy
                </Link>
              </li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="font-semibold mb-4">Connect</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="https://twitter.com/owasp_blt"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-bodydark hover:text-white transition-colors"
                >
                  Twitter
                </a>
              </li>
              <li>
                <a
                  href="https://www.facebook.com/groups/owaspfoundation/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-bodydark hover:text-white transition-colors"
                >
                  Facebook
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-strokedark mt-8 pt-6 text-center text-sm text-bodydark">
          <p>&copy; {new Date().getFullYear()} OWASP BLT. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
