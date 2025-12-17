
def test_login_with_invalid_username_shows_error(self):
    """Test that invalid username displays non-field error"""
    response = self.client.post('/accounts/login/', {
        'login': 'nonexistent_user',
        'password': 'wrongpassword'
    })
    self.assertContains(response, 'non_field_errors')
    # Verify error message is displayed

def test_login_with_invalid_email_shows_error(self):
    """Test that invalid email displays non-field error"""
    response = self.client.post('/accounts/login/', {
        'login': 'nonexistent@example.com',
        'password': 'wrongpassword'
    })
    self.assertContains(response, 'non_field_errors')

def test_login_with_email_success(self):
    """Test successful login using email instead of username"""
    user = User.objects.create_user('testuser', 'test@example.com', 'password123')
    EmailAddress.objects.create(user=user, email='test@example.com', verified=True, primary=True)
    
    response = self.client.post('/accounts/login/', {
        'login': 'test@example.com',
        'password': 'password123'
    })
    self.assertEqual(response.status_code, 302)  # Redirect on success

def test_login_with_username_success(self):
    """Test successful login using username (existing functionality)"""
    # Ensure username login still works
    user = User.objects.create_user('testuser', 'test@example.com', 'password123')
    EmailAddress.objects.create(user=user, email='test@example.com', verified=True, primary=True)
    
    response = self.client.post('/accounts/login/', {
        'login': 'testuser',
        'password': 'password123'
    })
    self.assertEqual(response.status_code, 302)