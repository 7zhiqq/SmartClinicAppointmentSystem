"""
Password Reset Diagnostic Script
Run in Django shell: python manage.py shell

Then:
exec(open('diagnose_reset.py').read())
"""

def diagnose_password_reset():
    from django.contrib.auth.forms import PasswordResetForm
    from accounts.models import User
    from django.conf import settings
    import traceback
    
    print("\n" + "="*70)
    print("PASSWORD RESET DIAGNOSTIC")
    print("="*70)
    
    # Step 1: Check user exists
    print("\n[STEP 1] Checking for test user...")
    email = input("Enter email address to test: ").strip()
    
    if not email:
        print("❌ No email provided")
        return
    
    try:
        user = User.objects.get(email__iexact=email)
        print(f"✅ User found:")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Full Name: {user.get_full_name()}")
        print(f"   Is Active: {user.is_active}")
        print(f"   Is Staff: {user.is_staff}")
        
        if not user.is_active:
            print("⚠️  WARNING: User is not active - password reset will not work!")
            
    except User.DoesNotExist:
        print(f"❌ ERROR: No user found with email '{email}'")
        print("\nTip: Email lookup is case-insensitive")
        
        # Show similar emails
        similar = User.objects.filter(email__icontains=email.split('@')[0])
        if similar.exists():
            print(f"\nFound {similar.count()} similar email(s):")
            for u in similar[:5]:
                print(f"   - {u.email}")
        return
    
    # Step 2: Check templates exist
    print("\n[STEP 2] Checking templates...")
    import os
    from django.template.loader import get_template
    
    templates_to_check = [
        'accounts/password_reset.html',
        'accounts/password_reset_email.html',
        'accounts/password_reset_subject.txt',
        'accounts/password_reset_done.html',
        'accounts/password_reset_confirm.html',
        'accounts/password_reset_complete.html',
    ]
    
    missing_templates = []
    for template_name in templates_to_check:
        try:
            get_template(template_name)
            print(f"✅ {template_name}")
        except Exception as e:
            print(f"❌ {template_name} - {str(e)}")
            missing_templates.append(template_name)
    
    if missing_templates:
        print(f"\n⚠️  WARNING: {len(missing_templates)} template(s) missing!")
    
    # Step 3: Test password reset form
    print("\n[STEP 3] Testing PasswordResetForm...")
    
    form_data = {'email': email}
    form = PasswordResetForm(data=form_data)
    
    if form.is_valid():
        print("✅ Form is valid")
    else:
        print(f"❌ Form validation failed: {form.errors}")
        return
    
    # Step 4: Try to send reset email
    print("\n[STEP 4] Attempting to send password reset email...")
    print("(This should actually send an email)")
    
    confirm = input("\nProceed with sending email? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Cancelled by user")
        return
    
    try:
        # Create a mock request object
        from django.http import HttpRequest
        from django.contrib.sites.shortcuts import get_current_site
        
        request = HttpRequest()
        request.META['SERVER_NAME'] = 'localhost'
        request.META['SERVER_PORT'] = '8000'
        
        print("\nSending...")
        
        result = form.save(
            request=request,
            use_https=False,
            from_email=settings.DEFAULT_FROM_EMAIL,
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
        )
        
        print(f"\n✅ SUCCESS! Password reset email sent to {email}")
        print("\nNext steps:")
        print("1. Check your email inbox")
        print("2. Check your spam/junk folder")
        print("3. Look for email from:", settings.DEFAULT_FROM_EMAIL)
        print("\nIf email still doesn't arrive:")
        print("- Check Gmail 'Sent' folder to confirm it was sent")
        print("- Try with a different email address")
        print("- Check server logs for errors")
        
    except Exception as e:
        print(f"\n❌ ERROR sending email:")
        print(f"   {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
    
    # Step 5: Show email settings
    print("\n[STEP 5] Current Email Settings:")
    print(f"   Backend: {settings.EMAIL_BACKEND}")
    print(f"   Host: {settings.EMAIL_HOST}")
    print(f"   Port: {settings.EMAIL_PORT}")
    print(f"   TLS: {settings.EMAIL_USE_TLS}")
    print(f"   From: {settings.DEFAULT_FROM_EMAIL}")
    print(f"   User: {settings.EMAIL_HOST_USER}")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    diagnose_password_reset()