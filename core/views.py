from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, Job, Transaction, Category, PromotedWorker, Product, OfflineService, OfflineBooking, Cart, CartItem, BranchAdminInvite, Order, OrderItem
from django.db import models as db_models, IntegrityError
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
import json
import uuid

def register_view(request):
    if request.method == 'POST':
        # Simplify registration for the demo
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_type = request.POST.get('user_type')
        email = request.POST.get('email')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')
            
        user = CustomUser.objects.create_user(
            username=username, 
            password=password, 
            email=email, 
            user_type=user_type
        )
        login(request, user)
        return redirect('dashboard_redirect')
        
    return render(request, 'core/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard_redirect')
        else:
            messages.error(request, 'Invalid credentials.')
            
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard_redirect(request):
    user_type = request.user.user_type
    if user_type == 'ADMIN':
        return redirect('admin_dashboard')
    elif user_type == 'PROVIDER':
        return redirect('provider_dashboard')
    elif user_type == 'WORKER':
        return redirect('worker_dashboard')
    elif user_type == 'CUSTOMER':
        return redirect('customer_dashboard')
    elif user_type == 'SELLER':
        return redirect('seller_dashboard')
    elif user_type == 'OFFLINE_PROVIDER':
        return redirect('offline_provider_dashboard')
    
    return redirect('login')

def homepage(request):
    """Public landing page showcasing platform features."""
    from .models import Product, OfflineService, Job
    featured_products = Product.objects.filter(stock__gt=0).order_by('-id')[:6]
    featured_services = OfflineService.objects.all().order_by('-id')[:6]
    open_jobs = Job.objects.filter(status='OPEN').order_by('-id')[:4]
    context = {
        'featured_products': featured_products,
        'featured_services': featured_services,
        'open_jobs': open_jobs,
    }
    return render(request, 'core/homepage.html', context)

@login_required
def user_profile(request, username):
    """Public/own profile page for any user type."""
    profile_user = get_object_or_404(CustomUser, username=username)
    is_own_profile = request.user == profile_user
    skills_list = [s.strip() for s in profile_user.skills.split(',') if s.strip()]
    context = {
        'profile_user': profile_user,
        'is_own_profile': is_own_profile,
        'skills_list': skills_list,
    }
    return render(request, 'core/user_profile.html', context)

@login_required
def edit_profile(request):
    """Allow logged-in user to edit their own profile information."""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.bio = request.POST.get('bio', user.bio)
        user.phone = request.POST.get('phone', user.phone)
        user.location = request.POST.get('location', user.location)
        user.skills = request.POST.get('skills', user.skills)
        if 'profile_image' in request.FILES:
            user.profile_image = request.FILES['profile_image']
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('user_profile', username=user.username)
    return render(request, 'core/edit_profile.html', {'user': request.user})

@login_required
def admin_dashboard(request):
    if request.user.user_type != 'ADMIN':
        return redirect('dashboard_redirect')
        
    context = {
        'total_users': CustomUser.objects.count(),
        'total_jobs': Job.objects.count(),
        'total_revenue': Transaction.objects.filter(transaction_type='RELEASE').aggregate(db_models.Sum('amount'))['amount__sum'] or 0,
        'recent_transactions': Transaction.objects.order_by('-timestamp')[:10],
        'user_stats': {
            'customers': CustomUser.objects.filter(user_type='CUSTOMER').count(),
            'sellers': CustomUser.objects.filter(user_type='SELLER').count(),
            'workers': CustomUser.objects.filter(user_type='WORKER').count(),
            'providers': CustomUser.objects.filter(user_type='PROVIDER').count(),
            'offline_providers': CustomUser.objects.filter(user_type='OFFLINE_PROVIDER').count(),
        }
    }
    return render(request, 'core/admin_dashboard.html', context)

@login_required
def admin_user_list(request):
    if request.user.user_type != 'ADMIN':
        return redirect('dashboard_redirect')
    
    query = request.GET.get('q', '')
    user_type = request.GET.get('type', '')
    
    users = CustomUser.objects.all().order_by('-date_joined')
    
    if query:
        users = users.filter(db_models.Q(username__icontains=query) | db_models.Q(email__icontains=query))
    if user_type:
        users = users.filter(user_type=user_type)
        
    context = {
        'users': users,
        'query': query,
        'user_type': user_type,
        'user_types': CustomUser.USER_TYPE_CHOICES
    }
    return render(request, 'core/admin_users.html', context)

@login_required
def admin_user_add(request):
    if request.user.user_type != 'ADMIN':
        return redirect('dashboard_redirect')
        
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        user_type = request.POST.get('user_type')
        is_verified = request.POST.get('is_verified') == 'on'
        
        if not username:
            messages.error(request, 'Username is required.')
        elif CustomUser.objects.filter(username__iexact=username).exists():
            messages.error(request, 'Username already exists.')
        elif email and CustomUser.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Email already exists.')
        else:
            try:
                user = CustomUser.objects.create_user(
                    username=username, 
                    email=email, 
                    password=password,
                    user_type=user_type,
                    is_verified=is_verified
                )
                messages.success(request, f'User {username} created successfully.')
                return redirect('admin_user_list')
            except IntegrityError:
                messages.error(request, 'A database error occurred. Possibly a duplicate username or email.')
            
    return render(request, 'core/admin_user_form.html', {'user_types': CustomUser.USER_TYPE_CHOICES})

@login_required
def admin_user_edit(request, user_id):
    if request.user.user_type != 'ADMIN':
        return redirect('dashboard_redirect')
        
    target_user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        user_type = request.POST.get('user_type')
        is_verified = request.POST.get('is_verified') == 'on'
        wallet_balance = request.POST.get('wallet_balance', 0)
        
        if not username:
            messages.error(request, 'Username is required.')
        elif CustomUser.objects.filter(username__iexact=username).exclude(id=user_id).exists():
            messages.error(request, 'Username already exists.')
        elif email and CustomUser.objects.filter(email__iexact=email).exclude(id=user_id).exists():
            messages.error(request, 'Email already exists.')
        else:
            try:
                target_user.username = username
                target_user.email = email
                target_user.user_type = user_type
                target_user.is_verified = is_verified
                target_user.wallet_balance = wallet_balance
                
                target_user.save()
                messages.success(request, f'User {target_user.username} updated successfully.')
                return redirect('admin_user_list')
            except IntegrityError:
                messages.error(request, 'A database error occurred. Possibly a duplicate username or email.')
        
    context = {
        'target_user': target_user,
        'user_types': CustomUser.USER_TYPE_CHOICES
    }
    return render(request, 'core/admin_user_form.html', context)

@login_required
def admin_user_delete(request, user_id):
    if request.user.user_type != 'ADMIN' or request.method != 'POST':
        return redirect('dashboard_redirect')
        
    target_user = get_object_or_404(CustomUser, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot delete yourself.")
    else:
        username = target_user.username
        target_user.delete()
        messages.success(request, f'User {username} deleted successfully.')
        
    return redirect('admin_user_list')

@login_required
def admin_analytics(request):
    if request.user.user_type != 'ADMIN':
        return redirect('dashboard_redirect')
    return render(request, 'core/admin_analytics.html')

@login_required
def admin_analytics_data(request):
    if request.user.user_type != 'ADMIN':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    # Get last 6 months of data
    six_months_ago = timezone.now() - timedelta(days=180)
    
    # User growth by type
    user_growth = CustomUser.objects.filter(date_joined__gte=six_months_ago)\
        .annotate(month=TruncMonth('date_joined'))\
        .values('month', 'user_type')\
        .annotate(count=db_models.Count('id'))\
        .order_by('month')

    # Job activity
    job_activity = Job.objects.filter(created_at__gte=six_months_ago)\
        .annotate(month=TruncMonth('created_at'))\
        .values('month', 'status')\
        .annotate(count=db_models.Count('id'))\
        .order_by('month')

    # Revenue
    revenue_data = Transaction.objects.filter(transaction_type='RELEASE', timestamp__gte=six_months_ago)\
        .annotate(month=TruncMonth('timestamp'))\
        .values('month')\
        .annotate(total=db_models.Sum('amount'))\
        .order_by('month')

    return JsonResponse({
        'user_growth': list(user_growth),
        'job_activity': list(job_activity),
        'revenue': list(revenue_data),
    })

@login_required
def admin_generate_passkey(request):
    if request.user.user_type != 'ADMIN':
        return redirect('dashboard_redirect')
        
    if request.method == 'POST':
        invite = BranchAdminInvite.objects.create(created_by=request.user)
        return render(request, 'core/admin_passkey.html', {'invite': invite})
        
    invites = BranchAdminInvite.objects.filter(created_by=request.user).order_by('-created_at')[:5]
    return render(request, 'core/admin_passkey.html', {'invites': invites})

@login_required
def admin_redeem_passkey(request):
    token_str = request.GET.get('token') or request.POST.get('token')
    
    if request.method == 'POST':
        try:
            invite = BranchAdminInvite.objects.get(token=token_str)
            if invite.is_valid():
                invite.is_used = True
                invite.used_by = request.user
                invite.save()
                
                request.user.user_type = 'ADMIN'
                request.user.save()
                
                messages.success(request, "Success! You are now an Admin.")
                return redirect('admin_dashboard')
            else:
                messages.error(request, "This passkey has expired or already been used.")
        except (BranchAdminInvite.DoesNotExist, ValueError):
            messages.error(request, "Invalid passkey.")
            
    return render(request, 'core/redeem_passkey.html', {'token': token_str})

@login_required
def provider_dashboard(request):
    if request.user.user_type != 'PROVIDER':
        return redirect('dashboard_redirect')
        
    context = {
        'posted_jobs': Job.objects.filter(provider=request.user),
        'wallet_balance': request.user.wallet_balance,
        'categories': Category.objects.all(),
    }
    return render(request, 'core/job_provider_dashboard.html', context)

@login_required
def worker_dashboard(request):
    if request.user.user_type != 'WORKER':
        return redirect('dashboard_redirect')
        
    context = {
        'my_jobs': Job.objects.filter(worker=request.user).order_by('-id'),
        'wallet_balance': request.user.wallet_balance
    }
    return render(request, 'core/worker_dashboard.html', context)

@login_required
def customer_dashboard(request):
    if request.user.user_type != 'CUSTOMER':
        return redirect('dashboard_redirect')
        
    context = {
        'wallet_balance': request.user.wallet_balance,
        'my_bookings': request.user.bookings_made.all().order_by('booking_date'),
        'my_orders': request.user.orders.all().order_by('-created_at')
    }
    return render(request, 'core/customer_dashboard.html', context)

@login_required
def seller_dashboard(request):
    if request.user.user_type != 'SELLER':
        return redirect('dashboard_redirect')
        
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        image = request.FILES.get('image')
        
        if name and price:
            Product.objects.create(
                seller=request.user,
                name=name,
                description=description,
                price=price,
                stock=stock or 1,
                image=image
            )
            messages.success(request, 'Product listed successfully!')
            return redirect('seller_dashboard')
            
    context = {
        'my_products': request.user.products.all(),
        'wallet_balance': request.user.wallet_balance,
        'incoming_orders': OrderItem.objects.filter(product__seller=request.user).order_by('-order__created_at')
    }
    return render(request, 'core/seller_dashboard.html', context)

@login_required
def offline_provider_dashboard(request):
    if request.user.user_type != 'OFFLINE_PROVIDER':
        return redirect('dashboard_redirect')
        
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        base_price = request.POST.get('base_price')
        location = request.POST.get('location')
        opening_time = request.POST.get('opening_time')
        closing_time = request.POST.get('closing_time')
        image = request.FILES.get('image')
        
        if title and base_price:
            OfflineService.objects.create(
                provider=request.user,
                title=title,
                description=description,
                base_price=base_price,
                location=location,
                opening_time=opening_time,
                closing_time=closing_time,
                image=image
            )
            messages.success(request, 'Service published successfully!')
            return redirect('offline_provider_dashboard')
            
    context = {
        'my_services': request.user.offline_services.all(),
        'upcoming_bookings': OfflineBooking.objects.filter(service__provider=request.user, status__in=['PENDING', 'CONFIRMED']).order_by('booking_date'),
        'wallet_balance': request.user.wallet_balance
    }
    return render(request, 'core/offline_provider_dashboard.html', context)

def marketplace(request):
    # Publicly accessible marketplace for all OPEN jobs
    category_id = request.GET.get('category')
    jobs = Job.objects.filter(status='OPEN')
    
    selected_category = None
    if category_id:
        if category_id == 'other':
            jobs = jobs.filter(category__isnull=True)
            selected_category = "Other / Uncategorized"
        else:
            try:
                selected_category = Category.objects.get(id=category_id)
                jobs = jobs.filter(category=selected_category)
            except (Category.DoesNotExist, ValueError):
                pass
                
    context = {
        'available_jobs': jobs.order_by('-id'),
        'selected_category': selected_category
    }
    return render(request, 'core/marketplace.html', context)

def products(request):
    sort_by = request.GET.get('sort_by', '')
    product_list = Product.objects.all()
    
    if sort_by == 'price_asc':
        product_list = product_list.order_by('price')
    elif sort_by == 'price_desc':
        product_list = product_list.order_by('-price')
    elif sort_by == 'name':
        product_list = product_list.order_by('name')
    else:
        product_list = product_list.order_by('-id')

    context = {
        'products': product_list,
        'sort_by': sort_by
    }
    return render(request, 'core/products.html', context)

def offline_services(request):
    sort_by = request.GET.get('sort_by', 'availability')
    location_query = request.GET.get('location', '').strip()
    
    services_list = OfflineService.objects.all()
    
    if location_query:
        services_list = services_list.filter(location__icontains=location_query)
        
    if sort_by == 'price_asc':
        services_list = services_list.order_by('base_price')
    elif sort_by == 'price_desc':
        services_list = services_list.order_by('-base_price')
    elif sort_by == 'availability' or not sort_by:
        # Simplistic availability: just order newest first. In a real app we'd sort by nearest/opening time
        services_list = services_list.order_by('-id')

    context = {
        'services': services_list,
        'sort_by': sort_by,
        'location_query': location_query
    }
    return render(request, 'core/offline_services.html', context)

@login_required
def book_offline_service(request, service_id):
    if request.method == 'POST':
        from django.utils.dateparse import parse_datetime
        from django.utils import timezone
        
        service = get_object_or_404(OfflineService, id=service_id)
        booking_time_str = request.POST.get('booking_time')
        notes = request.POST.get('notes', '')
        phone = request.POST.get('customer_phone', '')
        
        if not booking_time_str:
            messages.error(request, 'Please select a booking date and time.')
            return redirect('offline_services')
            
        if not phone:
            messages.error(request, 'Please provide a contact phone number.')
            return redirect('offline_services')

        booking_dt = parse_datetime(booking_time_str)
        if booking_dt is None:
            messages.error(request, 'Invalid date format.')
            return redirect('offline_services')
            
        if timezone.is_naive(booking_dt):
            booking_dt = timezone.make_aware(booking_dt)
            
        booking_time = booking_dt.time()
        
        if service.opening_time <= booking_time <= service.closing_time:
            booking = OfflineBooking.objects.create(
                customer=request.user,
                service=service,
                booking_date=booking_dt,
                customer_phone=phone,
                notes=notes
            )
            # Format time beautifully e.g. Oct 12, 2026 02:30 PM
            formatted_date = booking_dt.strftime("%b %d, %Y %I:%M %p")
            messages.success(request, f'Successfully booked {service.title} for {formatted_date}!')
            return redirect('booking_confirmation', booking_id=booking.id)
        else:
            messages.error(request, f'Selected time is outside operating hours ({service.opening_time.strftime("%I:%M %p")} - {service.closing_time.strftime("%I:%M %p")}).')
            
    return redirect('offline_services')

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(OfflineBooking, id=booking_id, customer=request.user)
    context = {
        'booking': booking
    }
    return render(request, 'core/booking_confirmation.html', context)

@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        if product.stock > 0:
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
            
            if not item_created:
                cart_item.quantity += 1
                cart_item.save()
            messages.success(request, f'Added {product.name} to your cart.')
        else:
            messages.error(request, 'This product is out of stock.')
    return redirect('products')

@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    context = {
        'cart': cart,
    }
    return render(request, 'core/cart.html', context)

@login_required
def checkout(request):
    if request.method == 'POST':
        cart, created = Cart.objects.get_or_create(user=request.user)
        if hasattr(cart, 'items') and cart.items.exists():
            total = cart.get_total_price()
            
            # Check buyer balance
            if request.user.wallet_balance < total:
                messages.error(request, f'Insufficient wallet balance. Total needed: ${total}')
                return redirect('view_cart')
            
            # Deduct from buyer
            request.user.wallet_balance -= total
            request.user.save()
            
            # Record buyer transaction
            Transaction.objects.create(
                job=None,
                user=request.user,
                amount=total,
                transaction_type='PURCHASE'
            )
            
            # Create Order record
            order = Order.objects.create(
                customer=request.user,
                total_price=total,
                status='PENDING'
            )
            
            # Simple stock deduction and seller payment logic
            for item in cart.items.all():
                if item.product.stock >= item.quantity:
                    # Create OrderItem
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )
                    
                    item.product.stock -= item.quantity
                    item.product.save()
                    
                    # Record transaction to seller
                    item.product.seller.wallet_balance += item.get_cost()
                    item.product.seller.save()
                    Transaction.objects.create(
                        job=None,
                        user=item.product.seller,
                        amount=item.get_cost(),
                        transaction_type='RELEASE'
                    )
                else:
                    # In a real app, you'd want to handle this better (e.g. refund if partial failure)
                    # For this demo, we assume stock is usually available if checked at start
                    messages.error(request, f'Not enough stock for {item.product.name}.')
                    
            cart.items.all().delete()
            messages.success(request, f'Successfully purchased items! Total paid: ${total}')
            return redirect('customer_dashboard')
        else:
            messages.error(request, 'Your cart is empty.')
    return redirect('view_cart')

def ai_assistant_mode(request):
    return render(request, 'core/ai_assistant.html')

def popular_services(request):
    # List categories and top promoted workers
    from django.db.models import Count, Q
    promoted_workers = PromotedWorker.objects.order_by('-promotion_bid', '-promoted_at')
    
    # Annotate categories with the count of jobs that have status='OPEN'
    categories = Category.objects.annotate(
        open_jobs_count=Count('jobs', filter=Q(jobs__status='OPEN'))
    )
    
    # Count jobs without a category
    other_jobs_count = Job.objects.filter(category__isnull=True, status='OPEN').count()
    
    open_provider_jobs = []
    if request.user.is_authenticated and request.user.user_type == 'PROVIDER':
        open_provider_jobs = Job.objects.filter(provider=request.user, status='OPEN').order_by('-created_at')
        
    context = {
        'promoted_workers': promoted_workers,
        'categories': categories,
        'other_jobs_count': other_jobs_count,
        'open_provider_jobs': open_provider_jobs,
    }
    return render(request, 'core/popular_services.html', context)


def worker_profile(request, username):
    worker = get_object_or_404(CustomUser, username=username, user_type='WORKER')
    reviews = worker.reviews_received.order_by('-created_at')
    completed_jobs = Job.objects.filter(worker=worker, status='COMPLETED').count()
    
    open_provider_jobs = []
    if request.user.is_authenticated and request.user.user_type == 'PROVIDER':
        open_provider_jobs = Job.objects.filter(provider=request.user, status='OPEN').order_by('-created_at')
        
    context = {
        'worker': worker,
        'reviews': reviews,
        'completed_jobs': completed_jobs,
        'open_provider_jobs': open_provider_jobs,
    }
    return render(request, 'core/worker_profile.html', context)

@login_required
def assign_job(request, username):
    if request.method == 'POST' and request.user.user_type == 'PROVIDER':
        worker = get_object_or_404(CustomUser, username=username, user_type='WORKER')
        job_id = request.POST.get('job_id')
        
        if job_id:
            job = get_object_or_404(Job, id=job_id, provider=request.user, status='OPEN')
            job.worker = worker
            job.status = 'IN_PROGRESS'
            job.save()
            messages.success(request, f'Successfully assigned "{job.title}" to {worker.username}!')
        else:
            messages.error(request, 'Please select a valid job to assign.')
            
    return redirect('worker_profile', username=username)

@login_required
def post_job(request):
    if request.user.user_type != 'PROVIDER':
        return redirect('dashboard_redirect')
        
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        
        from decimal import Decimal
        try:
            budget = Decimal(request.POST.get('budget', '0'))
        except:
            budget = Decimal('0')
            
        if budget > 0 and request.user.wallet_balance >= budget:
            # Deduct wallet
            request.user.wallet_balance -= budget
            request.user.save()
            
            # Create Job
            category_id = request.POST.get('category')
            category = Category.objects.filter(id=category_id).first() if category_id and category_id != 'other' else None
            
            job = Job.objects.create(
                title=title,
                category=category,
                description=description,
                budget=budget,
                featured_image=request.FILES.get('featured_image'),
                provider=request.user,
                is_deposited=True
            )
            
            # Record Transaction
            Transaction.objects.create(
                job=job,
                user=request.user,
                amount=budget,
                transaction_type='DEPOSIT'
            )
            messages.success(request, f'Job posted successfully! ${budget} securely held in Escrow.')
            return redirect('provider_dashboard')
        else:
            messages.error(request, 'Insufficient wallet balance for this budget.')
            
    categories = Category.objects.all()
    return render(request, 'core/post_job.html', {'categories': categories})

@login_required
def add_funds(request):
    if request.method == 'POST':
        try:
            from decimal import Decimal
            amount = Decimal(request.POST.get('amount', '0'))
            if amount > 0:
                request.user.wallet_balance += amount
                request.user.save()
                messages.success(request, f'Successfully added ${amount} to your wallet.')
            else:
                messages.error(request, 'Please enter a valid amount.')
        except:
            messages.error(request, 'Invalid amount.')
    
    # Dynamic redirect based on user type
    role_redirects = {
        'PROVIDER': 'provider_dashboard',
        'WORKER': 'worker_dashboard',
        'CUSTOMER': 'customer_dashboard',
        'SELLER': 'seller_dashboard',
        'OFFLINE_PROVIDER': 'offline_provider_dashboard',
        'ADMIN': 'admin_dashboard'
    }
    return redirect(role_redirects.get(request.user.user_type, 'dashboard_redirect'))

@login_required
def take_job(request, job_id):
    if request.method == 'POST' and request.user.user_type == 'WORKER':
        try:
            job = Job.objects.get(id=job_id, status='OPEN')
            job.worker = request.user
            job.status = 'IN_PROGRESS'
            job.save()
            messages.success(request, f'You have successfully taken the job: {job.title}')
        except Job.DoesNotExist:
            messages.error(request, 'Job is no longer available.')
            
    return redirect('worker_dashboard')

@login_required
def submit_work(request, job_id):
    if request.method == 'POST' and request.user.user_type == 'WORKER':
        try:
            job = Job.objects.get(id=job_id, worker=request.user, status='IN_PROGRESS')
            file_submission = request.FILES.get('file_submission')
            if file_submission:
                job.file_submission = file_submission
                job.status = 'SUBMITTED'
                job.save()
                messages.success(request, 'Work submitted successfully! Waiting for provider approval.')
            else:
                messages.error(request, 'No file uploaded.')
        except Job.DoesNotExist:
            messages.error(request, 'Job not found or not in progress.')
            
    return redirect('worker_dashboard')

@login_required
def approve_work(request, job_id):
    if request.method == 'POST' and request.user.user_type == 'PROVIDER':
        try:
            job = Job.objects.get(id=job_id, provider=request.user, status='SUBMITTED')
            
            # Transfer funds to worker
            worker = job.worker
            worker.wallet_balance += job.budget
            worker.save()
            
            # Update job status
            job.status = 'COMPLETED'
            job.save()
            
            # Record Transaction
            Transaction.objects.create(
                job=job,
                user=worker,
                amount=job.budget,
                transaction_type='RELEASE'
            )
            messages.success(request, f'Work approved! ${job.budget} released to {worker.username}.')
            # Trigger review prompt (optional redirect)
        except Job.DoesNotExist:
            messages.error(request, 'Invalid job or status.')
            
    return redirect('provider_dashboard')

@login_required
def reject_work(request, job_id):
    if request.method == 'POST' and request.user.user_type == 'PROVIDER':
        try:
            job = Job.objects.get(id=job_id, provider=request.user, status='SUBMITTED')
            
            # Reset the job status to allow the worker to resubmit
            job.status = 'IN_PROGRESS'
            # Remove the previous file submission (optional, but good for clean DB)
            if job.file_submission:
                job.file_submission.delete(save=False)
                job.file_submission = None
            job.save()
            
            messages.info(request, f'Submission rejected. The job has been sent back to {job.worker.username} for revision.')
        except Job.DoesNotExist:
            messages.error(request, 'Invalid job or status to reject.')
            
    return redirect('provider_dashboard')

@login_required
def delete_job(request, job_id):
    if request.method == 'POST' and request.user.user_type == 'PROVIDER':
        try:
            job = Job.objects.get(id=job_id, provider=request.user, status='OPEN')
            
            # Refund escrowed amount back to provider
            request.user.wallet_balance += job.budget
            request.user.save()
            
            # Record Refund Transaction
            Transaction.objects.create(
                job=None, # Job is about to be deleted
                user=request.user,
                amount=job.budget,
                transaction_type='REFUND'
            )
            
            job.delete()
            messages.success(request, f'Job "{job.title}" cancelled and ${job.budget} refunded to your wallet.')
        except Job.DoesNotExist:
            messages.error(request, 'You can only cancel jobs that are still OPEN and unassigned.')
            
    return redirect('provider_dashboard')

import os
from django.http import HttpResponse, Http404
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io

@login_required
def review_work_preview(request, job_id):
    """Anti-Cheating Preview logic"""
    try:
        job = Job.objects.get(id=job_id, provider=request.user, status='SUBMITTED')
        if not job.file_submission:
            raise Http404("No submission file found.")
            
        file_path = job.file_submission.path
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.png', '.jpg', '.jpeg']:
            # Apply Watermark
            img = Image.open(file_path).convert("RGBA")
            txt = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt)
            
            text = "GIGFLOW PREVIEW - DO NOT COPY"
            # Using default font due to likely unavailability of TTF
            font = ImageFont.load_default()
            
            # Calculate position to center watermark
            bbox = draw.textbbox((0, 0), text, font=font)
            left, top, right, bottom = bbox
            text_w = right - left
            text_h = bottom - top
            width, height = img.size
            position = ((width - text_w) / 2, (height - text_h) / 2)
            
            # Draw semi-transparent text - Darker and more opaque
            draw.text(position, text, fill=(150, 0, 0, 200), font=font)
            
            # Tile it or draw multiple for better protection - Darker tiled watermarks
            for i in range(0, width, 200):
                for j in range(0, height, 100):
                    draw.text((i, j), text, fill=(150, 0, 0, 100), font=font)
                    
            watermarked = Image.alpha_composite(img, txt)
            watermarked = watermarked.convert("RGB")
            
            response = HttpResponse(content_type="image/jpeg")
            watermarked.save(response, "JPEG")
            return response
            
        elif ext in ['.txt', '.md', '.csv']:
            # Truncate text logic
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Show only first 20% of text
            trunc_len = max(len(content) // 5, 20)
            preview_content = content[:trunc_len] + "\n\n... [GIGFLOW WATERMARK: REMAINDER SECURELY HIDDEN PENDING APPROVAL]"
            return HttpResponse(preview_content, content_type="text/plain")
            
        else:
            return HttpResponse("Preview not available for this file type. Please approve to download.", content_type="text/plain")
            
    except Job.DoesNotExist:
        raise Http404("Job not found.")

import json
import urllib.request
import urllib.parse
import urllib.error
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def chat_api(request):
    """
    Receives transcribed voice text from frontend,
    calls Gemini API (if key is set), and returns response text
    for TTS.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_text = data.get('text', '')
            
            api_key = getattr(settings, 'GEMINI_API_KEY', '')
            
            # Fetch platform context
            open_jobs = list(Job.objects.filter(status='OPEN')[:5].values('title', 'budget', 'id'))
            products = list(Product.objects.filter(stock__gt=0)[:5].values('name', 'price', 'id'))
            services = list(OfflineService.objects.all()[:5].values('title', 'base_price', 'id'))
            
            cart_context = ""
            if request.user.is_authenticated:
                cart, _ = Cart.objects.get_or_create(user=request.user)
                cart_items = list(cart.items.all().values('product__name', 'quantity'))
                if cart_items:
                    cart_context = f"\nUnpurchased Items in Cart: {cart_items}"
            
            context_str = f"Platform Data Context:\nJobs: {open_jobs}\nProducts: {products}\nServices: {services}{cart_context}\n"
            
            if not api_key:
                # If the key is not provided yet, fallback to a mocked response
                if 'hello' in user_text.lower():
                    reply = "Hello! I am Aria, your GigFlow assistant. Please set up the Gemini API key to unlock my full brain."
                elif 'job' in user_text.lower():
                    reply = f"I see {len(open_jobs)} open jobs right now. Set the API key to search them!"
                elif 'product' in user_text.lower() or 'buy' in user_text.lower():
                    reply = f"We have {len(products)} products in stock. Set the API key for details!"
                elif 'service' in user_text.lower():
                    reply = f"There are {len(services)} offline services available. Set the API key to explore!"
                else:
                    reply = "I heard you say: " + user_text + ". Please add the Gemini API key to activate full AI assistance."
                return JsonResponse({"response": reply})
                
            # Call Gemini API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": "You are Aria, the GigFlow AI assistant. Help users navigate a freelance and e-commerce marketplace. You have access to real platform data. " + context_str + " User says: " + user_text}]}]
            }).encode('utf-8')
            
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req) as response:
                    result = json.loads(response.read().decode())
                    # Extract text from Gemini response structure
                    reply_text = result['candidates'][0]['content']['parts'][0]['text']
                    
                return JsonResponse({"response": reply_text})
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    return JsonResponse({"response": "I am currently receiving too many requests on my API key. Please wait a moment and try again!"})
                else:
                    return JsonResponse({"response": f"I encountered an API error: {e.reason}. Please check the server logs."})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
            
    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def promote_worker(request):
    if request.method == 'POST' and request.user.user_type == 'WORKER':
        from decimal import Decimal
        try:
            bid_amount = Decimal(request.POST.get('bid_amount', '0'))
            if bid_amount > 0 and request.user.wallet_balance >= bid_amount:
                # Deduct from wallet
                request.user.wallet_balance -= bid_amount
                request.user.save()
                
                # Update or create promotion
                promotion, created = PromotedWorker.objects.get_or_create(worker=request.user)
                promotion.promotion_bid += bid_amount
                promotion.save()
                
                # Record transaction
                Transaction.objects.create(
                    job=None,
                    user=request.user,
                    amount=bid_amount,
                    transaction_type='PROMOTION'
                )
                
                messages.success(request, f'Successfully promoted your profile with ${bid_amount}!')
            else:
                messages.error(request, 'Insufficient wallet balance or invalid bid amount.')
        except Exception as e:
            messages.error(request, 'Invalid input.')
            
    return redirect('worker_dashboard')
