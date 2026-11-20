
import logging

import razorpay

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404, HttpResponse, FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import strip_tags
from django.views import generic
from django.views.decorators.http import require_POST

from .forms import ReviewForm
from .models import Ebook, Order, Note, Review, SurvivalPack


logger = logging.getLogger(__name__)


def get_razorpay_client():
    return razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )


def create_product_checkout(request, product, is_pack=False):
    """Create a Razorpay order for an ebook or survival pack."""

    if Order.objects.filter(
        user=request.user,
        ebook=product if not is_pack else None,
        survival_pack=product if is_pack else None,
        status='paid'
    ).exists():
        return HttpResponse(
            "You have already purchased this product.",
            status=400
        )

    amount_paise = int(product.price * 100)

    if amount_paise <= 0:
        return HttpResponse("Invalid product price.", status=400)

    client = get_razorpay_client()

    payment_order = client.order.create({
        'amount': amount_paise,
        'currency': 'INR',
        'payment_capture': 1
    })

    order_data = {
        'user': request.user,
        'amount': product.price,
        'razorpay_order_id': payment_order['id'],
    }

    if is_pack:
        order_data['survival_pack'] = product
    else:
        order_data['ebook'] = product

    order = Order.objects.create(**order_data)

    return render(request, 'store/checkout.html', {
        'ebook': product,
        'product': product,
        'order': order,
        'amount_paise': amount_paise,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'is_pack': is_pack,
    })


def landing_page(request):
    return render(request, 'store/landing.html')


def home(request):
    ebooks = Ebook.objects.filter(is_published=True)
    notes = Note.objects.all().order_by('-created_at')
    packs = SurvivalPack.objects.filter(is_published=True)
    reviews = Review.objects.all().order_by('-created_at')

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')

        form = ReviewForm(request.POST)

        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.save()
            return redirect('home')
    else:
        form = ReviewForm()

    return render(request, 'store/home.html', {
        'ebooks': ebooks,
        'notes': notes,
        'packs': packs,
        'reviews': reviews,
        'form': form
    })


@login_required
def checkout(request, slug):
    ebook = get_object_or_404(
        Ebook,
        slug=slug,
        is_published=True
    )

    return create_product_checkout(request, ebook)


@login_required
def pack_checkout(request, pack_id):
    pack = get_object_or_404(
        SurvivalPack,
        id=pack_id,
        is_published=True
    )

    return create_product_checkout(request, pack, is_pack=True)


@login_required
def dashboard(request):
    orders = Order.objects.filter(
        user=request.user,
        status='paid'
    ).order_by('-created_at')

    return render(request, 'store/dashboard.html', {
        'orders': orders
    })


class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'store/signup.html'


@login_required
@require_POST
def payment_verify(request):
    payment_id = request.POST.get('razorpay_payment_id', '').strip()
    razorpay_order_id = request.POST.get('razorpay_order_id', '').strip()
    signature = request.POST.get('razorpay_signature', '').strip()

    if not payment_id or not razorpay_order_id or not signature:
        return HttpResponse(
            "Payment verification details are missing.",
            status=400
        )

    try:
        order = Order.objects.get(
            razorpay_order_id=razorpay_order_id,
            user=request.user
        )

        client = get_razorpay_client()

        # Verify Razorpay payment signature.
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })

        # Fetch payment directly from Razorpay.
        payment = client.payment.fetch(payment_id)

        expected_amount = int(order.amount * 100)

        # Verify payment belongs to this order and has correct amount.
        if payment.get('order_id') != order.razorpay_order_id:
            return HttpResponse(
                "Payment order mismatch.",
                status=400
            )

        if payment.get('amount') != expected_amount:
            return HttpResponse(
                "Payment amount mismatch.",
                status=400
            )

        if payment.get('currency') != 'INR':
            return HttpResponse(
                "Payment currency mismatch.",
                status=400
            )

        if payment.get('status') != 'captured':
            return HttpResponse(
                "Payment is not captured yet. Please contact support.",
                status=400
            )

        # Lock the order to prevent duplicate processing.
        with transaction.atomic():
            locked_order = Order.objects.select_for_update().get(
                pk=order.pk,
                user=request.user
            )

            if locked_order.status == 'paid':
                if locked_order.razorpay_payment_id != payment_id:
                    return HttpResponse(
                        "This order has already been paid.",
                        status=400
                    )

                newly_paid = False

            elif locked_order.status == 'pending':
                newly_paid = locked_order.mark_paid(
                    payment_id,
                    signature
                )

            else:
                return HttpResponse(
                    "This order cannot be processed.",
                    status=400
                )

        # Send receipt only on the first successful payment transition.
        if newly_paid and request.user.email:
            try:
                download_link = request.build_absolute_uri(
                    reverse(
                        'download_ebook',
                        kwargs={'token': locked_order.download_token}
                    )
                )

                html_message = render_to_string(
                    'store/email_receipt.html',
                    {
                        'user': request.user,
                        'order': locked_order,
                        'download_link': download_link
                    }
                )

                send_mail(
                    subject=f"Your Purchase is Ready! - {locked_order.product_title}",
                    message=strip_tags(html_message),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    html_message=html_message,
                    fail_silently=False
                )

            except Exception:
                logger.exception(
                    "Receipt email failed for order %s",
                    locked_order.pk
                )

        return render(request, 'store/success.html', {
            'order': locked_order
        })

    except Order.DoesNotExist:
        return HttpResponse(
            "Order not found.",
            status=404
        )

    except razorpay.errors.SignatureVerificationError:
        logger.warning(
            "Razorpay signature verification failed for user %s",
            request.user.pk
        )
        return HttpResponse(
            "Payment verification failed. Please contact support.",
            status=400
        )

    except Exception:
        logger.exception(
            "Payment verification error for user %s",
            request.user.pk
        )
        return HttpResponse(
            "We could not verify your payment. Please contact support.",
            status=500
        )


@login_required
def download_ebook(request, token):
    order = get_object_or_404(
        Order,
        download_token=token,
        user=request.user
    )

    if order.status != 'paid':
        raise Http404("Payment not completed.")

    if order.ebook_id:
        product = order.ebook
    elif order.survival_pack_id:
        product = order.survival_pack
    else:
        raise Http404("Product not found.")

    if not product.pdf_file:
        raise Http404("PDF file missing.")

    try:
        file = product.pdf_file.open('rb')

        return FileResponse(
            file,
            as_attachment=True,
            filename=f"{product.title}.pdf",
            content_type="application/pdf"
        )

    except Exception:
        logger.exception(
            "Download failed for order %s",
            order.pk
        )
        raise Http404("PDF file could not be accessed.")


def privacy_policy(request):
    return render(request, 'store/privacy.html')


def terms(request):
    return render(request, 'store/terms.html')


def refund_policy(request):
    return render(request, 'store/refund.html')


def free_notes(request):
    notes = Note.objects.all().order_by('-created_at')

    branch = request.GET.get('branch')
    semester = request.GET.get('semester')

    if branch:
        notes = notes.filter(branch=branch)

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
        raise Http404("File missing.")

    try:
        file = note.pdf_file.open('rb')

        return FileResponse(
            file,
            as_attachment=True,
            filename=f"{note.title}.pdf",
            content_type="application/pdf"
        )

    except Exception:
        logger.exception(
            "Free note download failed for note %s",
            note.pk
        )
        raise Http404("PDF file could not be accessed.")
