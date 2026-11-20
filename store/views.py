from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from .models import Ebook, Order
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import SurvivalPack
import razorpay
import hmac
import hashlib

from .forms import ReviewForm
from .models import Review

def home(request):
    ebooks = Ebook.objects.filter(is_published=True)
    notes = Note.objects.all().order_by('-created_at')
    packs = SurvivalPack.objects.filter(is_published=True) # Naya
    reviews = Review.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        if request.user.is_authenticated:
            form = ReviewForm(request.POST)
            if form.is_valid():
                review = form.save(commit=False)
                review.user = request.user
                review.save()
                return redirect('home')
        else:
            return redirect('login')
    else:
        form = ReviewForm()

    return render(request, 'store/home.html', {
        'ebooks': ebooks, 
        'notes': notes, 
        'packs': packs, # Naya
        'reviews': reviews, 
        'form': form
    })

@login_required
def checkout(request, slug):
    ebook = get_object_or_404(Ebook, slug=slug)
    
    # Check if already bought
    if Order.objects.filter(user=request.user, ebook=ebook, status='paid').exists():
        return HttpResponse("Bhai, tu ye ebook pehle hi kharid chuka hai!")

    # Razorpay Order Create karo
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    order_amount = int(ebook.price * 100)
    order_currency = 'INR'
    payment_order = client.order.create(dict(amount=order_amount, currency=order_currency, payment_capture='1'))
    
    # Database mein save karo
    order = Order.objects.create(
        user=request.user, 
        ebook=ebook, 
        amount=ebook.price,
        razorpay_order_id=payment_order['id']
    )
    
    context = {
        'ebook': ebook,
        'order': order,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'store/checkout.html', context)

@login_required
def dashboard(request):
    # Sirf 'paid' status wali orders dikhao
    orders = Order.objects.filter(user=request.user, status='paid').order_by('-created_at')
    return render(request, 'store/dashboard.html', {'orders': orders})
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic

class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'store/signup.html'
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import razorpay
import hmac
import hashlib

@csrf_exempt
@login_required
def payment_verify(request):
    if request.method == "POST":
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id, user=request.user)
            
            # Razorpay Signature Verify Logic
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            client.utility.verify_payment_signature(params_dict)
            order.mark_paid(razorpay_payment_id, razorpay_signature)
            
            # 🚀 YAHAN SE EMAIL BHEJNA SHURU HOTA HAI
            download_link = f"http://127.0.0.1:8000/download/{order.download_token}/"
            
            # HTML email template render karo
            html_message = render_to_string('store/email_receipt.html', {
                'user': request.user,
                'order': order,
                'download_link': download_link
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f"Your eBook is Ready! - {order.ebook.title}",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                html_message=html_message,
                fail_silently=False,
            )
            # 🚀 EMAIL CODE KHATAM
            
            return render(request, 'store/success.html', {'order': order})
            
        except Exception as e:
            return HttpResponse(f"Payment Failed or Verification Error: {str(e)}")
            
    return HttpResponse("Invalid Request")
from django.http import FileResponse, Http404

@login_required
def download_ebook(request, token):
    order = get_object_or_404(
        Order,
        download_token=token,
        user=request.user
    )

    if order.status != 'paid':
        raise Http404("Payment not completed!")

    if not order.ebook or not order.ebook.pdf_file:
        raise Http404("PDF file missing!")

    try:
        file = order.ebook.pdf_file.open('rb')

        return FileResponse(
            file,
            as_attachment=True,
            filename=f"{order.ebook.title}.pdf",
            content_type="application/pdf"
        )
    except Exception:
        raise Http404("PDF file could not be accessed")
def privacy_policy(request):
    return render(request, 'store/privacy.html')

def terms(request):
    return render(request, 'store/terms.html')

def refund_policy(request):
    return render(request, 'store/refund.html')
def landing_page(request):
    return render(request, 'store/landing.html')
from .models import Note

def free_notes(request):
    notes = Note.objects.all().order_by('-created_at')
    
    # URL se branch aur semester ki value uthao
    branch = request.GET.get('branch')
    semester = request.GET.get('semester')
    
    # Agar user ne branch select kiya hai, toh filter karo
    if branch:
        notes = notes.filter(branch=branch)
        
    # Agar user ne semester select kiya hai, toh filter karo
    if semester:
        notes = notes.filter(semester=semester)

    context = {
        'notes': notes,
        'branches': Note.BRANCH_CHOICES,
        'semesters': Note.SEMESTER_CHOICES,
        'selected_branch': branch,
        'selected_semester': semester,
    }
    return render(request, 'store/notes.html', context)


def download_note(request, note_id):
    note = get_object_or_404(Note, id=note_id)

    if not note.pdf_file:
        raise Http404("File missing")

    try:
        file = note.pdf_file.open('rb')

        return FileResponse(
            file,
            as_attachment=True,
            filename=f"{note.title}.pdf",
            content_type="application/pdf"
        )

    except Exception:
        raise Http404("PDF file could not be accessed")

@login_required
def pack_checkout(request, pack_id):
    pack = get_object_or_404(SurvivalPack, id=pack_id)
    
    if Order.objects.filter(user=request.user, ebook=pack, status='paid').exists():
        return HttpResponse("Bhai, tu ye pack pehle hi kharid chuka hai!")

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    order_amount = int(pack.price * 100)
    payment_order = client.order.create(dict(amount=order_amount, currency='INR', payment_capture='1'))
    
    order = Order.objects.create(
        user=request.user, 
        ebook=pack, # Hum pack ko ebook ki tarah treat kar rahe hain
        amount=pack.price,
        razorpay_order_id=payment_order['id']
    )
    
    context = {
        'ebook': pack, 
        'order': order,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'is_pack': True, # Template mein pata chalne ke liye
    }
    return render(request, 'store/checkout.html', context)