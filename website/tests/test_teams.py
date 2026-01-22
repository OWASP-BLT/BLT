def test_leaderboard_requires_login_and_orders_correctly(self):
    """Test view requires auth and orders by score/streak"""
    # Unauthenticated access
    response = self.client.get(reverse("team_member_leaderboard"))
    self.assertEqual(response.status_code, 302)  # Redirect to login

    # Create team members with different scores
    user2 = User.objects.create_user(username="user2", password="test")
    user2.userprofile.team = self.team
    user2.userprofile.leaderboard_score = 150
    user2.userprofile.save()

    # Authenticated access
    self.client.login(username="testuser", password="testpass123")
    response = self.client.get(reverse("team_member_leaderboard"))

    self.assertEqual(response.status_code, 200)
    members = list(response.context["members"])
    # Higher score should be first
    self.assertEqual(members[0].user.username, "user2")
