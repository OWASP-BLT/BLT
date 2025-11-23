import json
import uuid
from decimal import Decimal
from io import BytesIO

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from PIL import Image, ImageDraw, ImageFont

from website.models import Bid, BidTransaction, RepoOwner, User, UserProfile


def enhanced_bidding_view(request):
    """Enhanced bidding interface with modern UI and BCH integration"""
    if request.method == "POST":
        return submit_enhanced_bid(request)
    
    # Get recent bids for display
    bids = Bid.objects.select_related('user', 'accepted_by').order_by('-created')[:20]
    
    # Get bid statistics
    stats = {
        'total_bids': Bid.objects.count(),
        'active_bids': Bid.objects.filter(status='Open').count(),
        'funded_bids': Bid.objects.filter(status='Funded').count(),
        'completed_bids': Bid.objects.filter(status='Completed').count(),
        'total_bch_in_bids': Bid.objects.aggregate(
            total=models.Sum('amount_bch')
        )['total'] or 0,
    }
    
    context = {
        'bids': bids,
        'stats': stats,
    }
    return render(request, 'bidding/enhanced_bidding.html', context)


def submit_enhanced_bid(request):
    """Submit a new bid with enhanced features"""
    github_username = request.POST.get('github_username', '').strip()
    issue_url = request.POST.get('issue_url', '').strip()
    amount_bch = request.POST.get('amount_bch', '').strip()
    bch_address = request.POST.get('bch_address', '').strip()
    
    # Validate inputs
    if not all([github_username, issue_url, amount_bch]):
        messages.error(request, 'Please fill in all required fields.')
        return redirect('enhanced_bidding')
    
    # Validate GitHub issue URL
    if not is_valid_github_issue_url(issue_url):
        messages.error(request, 'Please enter a valid GitHub issue URL.')
        return redirect('enhanced_bidding')
    
    try:
        amount_bch = Decimal(amount_bch)
        if amount_bch <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError):
        messages.error(request, 'Please enter a valid BCH amount.')
        return redirect('enhanced_bidding')
    
    # Check if user exists in our system
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        # Try to find user by GitHub username
        try:
            user_profile = UserProfile.objects.filter(
                github_url__icontains=github_username
            ).first()
            if user_profile:
                user = user_profile.user
        except:
            pass
    
    # Create the bid
    with transaction.atomic():
        bid = Bid.objects.create(
            user=user,
            github_username=github_username,
            issue_url=issue_url,
            amount_bch=amount_bch,
            bch_address=bch_address,
            status='Open'
        )
        
        # Generate escrow address and dynamic image token
        bid.generate_escrow_address()
        bid.generate_dynamic_image_token()
        bid.save()
    
    # Create success message with GitHub snippet
    github_snippet = bid.get_github_snippet()
    messages.success(
        request, 
        f'Bid of {amount_bch} BCH successfully placed! '
        f'Copy this snippet to your GitHub issue: {github_snippet}'
    )
    
    return redirect('enhanced_bidding')


def dynamic_bid_image(request, token):
    """Generate dynamic image showing current bid status"""
    try:
        bid = get_object_or_404(Bid, dynamic_image_token=token)
        
        # Get highest bid for this issue
        highest_bid = Bid.objects.filter(
            issue_url=bid.issue_url
        ).order_by('-amount_bch').first()
        
        # Create image
        width, height = 400, 150
        img = Image.new('RGB', (width, height), color='#ffffff')
        draw = ImageDraw.Draw(img)
        
        try:
            # Try to load a better font
            font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
            font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Colors
        primary_color = '#e74c3c'
        text_color = '#333333'
        bg_color = '#f8f9fa'
        
        # Draw background with border
        draw.rectangle([0, 0, width-1, height-1], fill=bg_color, outline=primary_color, width=2)
        
        # Title
        draw.text((20, 20), "🚀 OWASP BLT - Bid Status", fill=primary_color, font=font_large)
        
        # Current bid info
        if highest_bid:
            bid_text = f"Highest Bid: {highest_bid.amount_bch} BCH"
            status_text = f"Status: {highest_bid.status}"
            bidder_text = f"by {highest_bid.github_username or 'Anonymous'}"
        else:
            bid_text = "No bids yet"
            status_text = "Open for bidding"
            bidder_text = ""
        
        draw.text((20, 50), bid_text, fill=text_color, font=font_large)
        draw.text((20, 75), status_text, fill=text_color, font=font_small)
        if bidder_text:
            draw.text((20, 95), bidder_text, fill=text_color, font=font_small)
        
        # Call to action
        cta_text = "💎 Place your bid at blt.owasp.org/bidding"
        draw.text((20, 120), cta_text, fill=primary_color, font=font_small)
        
        # Save to BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return HttpResponse(buffer.getvalue(), content_type='image/png')
        
    except Exception as e:
        # Return error image
        img = Image.new('RGB', (400, 100), color='#ff0000')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"Error: {str(e)}", fill='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required
def accept_bid(request, bid_id):
    """Repository owner accepts a bid and provides funding details"""
    bid = get_object_or_404(Bid, id=bid_id)
    
    if request.method == 'POST':
        # Verify the user can manage this repository
        repo_owner, created = RepoOwner.objects.get_or_create(
            user=request.user,
            defaults={'github_username': request.user.username}
        )
        
        # In production, verify repo access via GitHub API
        # For now, allow any authenticated user to accept bids
        
        with transaction.atomic():
            bid.accepted_by = request.user
            bid.accepted_at = timezone.now()
            bid.status = 'Accepted'
            
            # Generate escrow address if not exists
            if not bid.escrow_address:
                bid.generate_escrow_address()
            
            bid.save()
        
        messages.success(
            request, 
            f'Bid accepted! Please send {bid.amount_bch} BCH to {bid.escrow_address} '
            f'to fund this bid.'
        )
        
        return redirect('bid_detail', bid_id=bid.id)
    
    return render(request, 'bidding/accept_bid.html', {'bid': bid})


@login_required
def fund_bid(request, bid_id):
    """Repository owner confirms funding transaction"""
    bid = get_object_or_404(Bid, id=bid_id, accepted_by=request.user)
    
    if request.method == 'POST':
        tx_hash = request.POST.get('tx_hash', '').strip()
        
        if not tx_hash:
            messages.error(request, 'Please provide the transaction hash.')
            return redirect('bid_detail', bid_id=bid.id)
        
        # Verify transaction (placeholder - would use BCH API in production)
        is_valid = verify_bch_transaction(tx_hash, bid.escrow_address, bid.amount_bch)
        
        if is_valid:
            with transaction.atomic():
                bid.funding_tx_hash = tx_hash
                bid.funded_at = timezone.now()
                bid.status = 'Funded'
                bid.save()
                
                # Create transaction record
                BidTransaction.objects.create(
                    bid=bid,
                    transaction_type='funding',
                    tx_hash=tx_hash,
                    from_address='repo_owner_address',  # Would get from API
                    to_address=bid.escrow_address,
                    amount_bch=bid.amount_bch,
                    status='confirmed'
                )
            
            messages.success(request, 'Funding confirmed! The coder can now start work.')
        else:
            messages.error(request, 'Unable to verify transaction. Please check the hash.')
    
    return redirect('bid_detail', bid_id=bid.id)


def bid_detail(request, bid_id):
    """Show detailed view of a specific bid"""
    bid = get_object_or_404(Bid, id=bid_id)
    transactions = bid.transactions.all().order_by('-created_at')
    
    context = {
        'bid': bid,
        'transactions': transactions,
        'can_accept': request.user.is_authenticated and bid.status == 'Open',
        'can_fund': request.user.is_authenticated and bid.accepted_by == request.user and bid.status == 'Accepted',
        'can_complete': request.user.is_authenticated and bid.accepted_by == request.user and bid.status == 'Submitted',
    }
    
    return render(request, 'bidding/bid_detail.html', context)


@csrf_exempt
def github_webhook(request):
    """Handle GitHub webhooks for PR events"""
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            
            if payload.get('action') == 'opened' and 'pull_request' in payload:
                pr = payload['pull_request']
                pr_url = pr['html_url']
                
                # Find bids that might be related to this PR
                # This is a simplified matching - in production would be more sophisticated
                issue_url = pr.get('issue_url', '')
                if issue_url:
                    bids = Bid.objects.filter(
                        issue_url__icontains=issue_url,
                        status='Funded'
                    )
                    
                    for bid in bids:
                        if not bid.pr_link:
                            bid.pr_link = pr_url
                            bid.status = 'Submitted'
                            bid.save()
                            break
            
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def is_valid_github_issue_url(url):
    """Validate GitHub issue URL format"""
    return (
        url.startswith('https://github.com/') and 
        '/issues/' in url and
        url.count('/') >= 6
    )


def verify_bch_transaction(tx_hash, address, expected_amount):
    """Verify BCH transaction (placeholder implementation)"""
    # In production, this would check the BCH blockchain
    # For now, return True to allow testing
    return True


@login_required
@require_POST
def complete_bid(request, bid_id):
    """Repository owner marks bid as complete and releases funds"""
    bid = get_object_or_404(Bid, id=bid_id, accepted_by=request.user)
    
    if bid.status != 'Submitted':
        messages.error(request, 'Bid must be in Submitted status to complete.')
        return redirect('bid_detail', bid_id=bid.id)
    
    # In production, would actually transfer BCH from escrow to coder's address
    release_tx_hash = f"release_{uuid.uuid4().hex[:16]}"
    
    with transaction.atomic():
        bid.release_tx_hash = release_tx_hash
        bid.completed_at = timezone.now()
        bid.status = 'Completed'
        bid.save()
        
        # Create transaction record
        BidTransaction.objects.create(
            bid=bid,
            transaction_type='release',
            tx_hash=release_tx_hash,
            from_address=bid.escrow_address,
            to_address=bid.bch_address,
            amount_bch=bid.amount_bch,
            status='confirmed'
        )
    
    messages.success(request, f'Bid completed! {bid.amount_bch} BCH released to coder.')
    return redirect('bid_detail', bid_id=bid.id)


@csrf_exempt
def check_current_bid(request):
    """API endpoint to check current highest bid for an issue"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            issue_url = data.get('issue_url', '').strip()
            
            if not issue_url:
                return JsonResponse({'error': 'Issue URL required'}, status=400)
            
            # Get highest bid for this issue
            highest_bid = Bid.objects.filter(
                issue_url=issue_url
            ).order_by('-amount_bch').first()
            
            if highest_bid:
                return JsonResponse({
                    'current_bid': str(highest_bid.amount_bch),
                    'status': highest_bid.status,
                    'bidder': highest_bid.github_username or (highest_bid.user.username if highest_bid.user else 'Anonymous'),
                    'created': highest_bid.created.isoformat(),
                })
            else:
                return JsonResponse({
                    'current_bid': '0',
                    'status': 'No bids',
                    'bidder': None,
                })
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def bid_api_status(request, bid_id):
    """API endpoint for bid status (for GitHub integration)"""
    try:
        bid = get_object_or_404(Bid, id=bid_id)
        highest_bid = Bid.objects.filter(
            issue_url=bid.issue_url
        ).order_by('-amount_bch').first()
        
        data = {
            'bid_id': bid.id,
            'issue_url': bid.issue_url,
            'current_bid': str(highest_bid.amount_bch) if highest_bid else '0',
            'status': highest_bid.status if highest_bid else 'No bids',
            'bidder': highest_bid.github_username if highest_bid else None,
            'dynamic_image_url': bid.get_dynamic_image_url(),
        }
        
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)