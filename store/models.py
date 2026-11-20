from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Ebook(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    author = models.CharField(max_length=100, default='Your Name')
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=499)
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='ebooks/', help_text='Actual PDF file')
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    ebook = models.ForeignKey(Ebook, on_delete=models.PROTECT)
    survival_pack = models.ForeignKey(
    'SurvivalPack',
    on_delete=models.PROTECT,
    null=True,
    blank=True
)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)
    download_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"#{self.id} - {self.user.username} - {self.ebook.title}"

    def mark_paid(self, payment_id, signature):
        self.status = 'paid'
        self.razorpay_payment_id = payment_id
        self.razorpay_signature = signature
        self.paid_at = timezone.now()
        self.save()
class Note(models.Model):
    BRANCH_CHOICES = [
        ('CSE', 'Computer Science and Engineering'),
        ('MEP', 'Mechanical Engineering and Production'),
        # Apne hisaab se aur add kar lena
    ]
    SEMESTER_CHOICES = [
        ('1', '1st Semester'),
        ('2', '2nd Semester'),
        ('3', '3rd Semester'),
        ('4', '4th Semester'),
        ('5', '5th Semester'),
        ('6', '6th Semester'),
    ]

    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100)
    branch = models.CharField(max_length=10, choices=BRANCH_CHOICES, default='CSE')
    semester = models.CharField(max_length=2, choices=SEMESTER_CHOICES, default='1')
    description = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='notes/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.branch} - Sem {self.semester})"

    def __str__(self):
        return f"{self.title} - {self.subject}"
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)]) # 1 to 5 stars
    feedback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.rating} Stars"    

class SurvivalPack(models.Model):
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=99)
    pdf_file = models.FileField(upload_to='survival_packs/')
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.subject}"    