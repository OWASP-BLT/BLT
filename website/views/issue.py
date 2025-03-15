# Update the view count to reflect unique visitor count based on IP log records
        unique_views = IP.objects.filter(issuenumber=self.object.id).values("address").distinct().count()
        self.object.views = unique_views
        self.object.save(update_fields=["views"])