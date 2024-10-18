from django.contrib import admin
from .models import Internship, Material, MaterialProgress, StageProgress

admin.site.register(Internship)
admin.site.register(Material)
admin.site.register(MaterialProgress)
admin.site.register(StageProgress)