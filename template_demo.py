"""
Template Usage Examples
Demonstrates how to use the different HTML templates stored in the templates/ directory
"""

from email_send import (
    ConfigManager, 
    EmailAutomationSystem, 
    EmailTemplateEngine
)
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demo_professional_template():
    """Demo using the professional template"""
    print("\n" + "="*60)
    print("DEMO: Professional Email Template")
    print("="*60)
    
    try:
        # Load configuration
        config_data = ConfigManager.load_config()
        email_config = ConfigManager.create_email_config(config_data)
        settings = config_data.get('settings', {})
        
        # Load professional template from file
        professional_template = EmailTemplateEngine.load_template_from_file("templates/professional_email_template.html")
        
        print("✅ Professional template loaded successfully")
        print(f"📏 Template size: {len(professional_template)} characters")
        
        # Sample emails for demo
        email_list = ["demo.user@company.com"]
        
        # Initialize automation system
        automation = EmailAutomationSystem(email_config, settings)
        
        # Process with professional template
        results = automation.process_email_list(
            email_list=email_list,
            subject_template="🌟 Professional Welcome, {first_name}!",
            body_template=professional_template,
            save_results=False  # Don't save for demo
        )
        
        print(f"🎯 Template loaded from: templates/professional_email_template.html")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")

def demo_simple_template():
    """Demo using the simple template"""
    print("\n" + "="*60)
    print("DEMO: Simple Welcome Template")
    print("="*60)
    
    try:
        # Load simple template from file
        simple_template = EmailTemplateEngine.load_template_from_file("templates/simple_welcome_template.html")
        
        print("✅ Simple template loaded successfully")
        print(f"📏 Template size: {len(simple_template)} characters")
        print(f"🎯 Template loaded from: templates/simple_welcome_template.html")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")

def demo_custom_invitation_template():
    """Demo using the custom invitation template"""
    print("\n" + "="*60)
    print("DEMO: Custom Invitation Template")
    print("="*60)
    
    try:
        # Load custom invitation template from file
        invitation_template = EmailTemplateEngine.load_template_from_file("templates/custom_invitation_template.html")
        
        print("✅ Custom invitation template loaded successfully")
        print(f"📏 Template size: {len(invitation_template)} characters")
        print(f"🎯 Template loaded from: templates/custom_invitation_template.html")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")

def demo_config_file_reference():
    """Demo using template file reference in config.json"""
    print("\n" + "="*60)
    print("DEMO: Template File Reference in Config")
    print("="*60)
    
    try:
        # Load configuration which references template file
        config_data = ConfigManager.load_config()
        
        templates = config_data.get('email_templates', {})
        body_config = templates.get('welcome_body', '')
        
        print(f"📋 Config template setting: {body_config}")
        
        if body_config.startswith('TEMPLATE_FILE:'):
            template_path = body_config.replace('TEMPLATE_FILE:', '')
            print(f"🎯 Template file path: {template_path}")
            
            # Load the template
            template_content = EmailTemplateEngine.load_template_from_file(template_path)
            print(f"✅ Template loaded successfully ({len(template_content)} characters)")
        else:
            print("ℹ️  No template file reference found in config")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")

def demo_template_fallback():
    """Demo template fallback when file is missing"""
    print("\n" + "="*60)
    print("DEMO: Template Fallback Mechanism")
    print("="*60)
    
    try:
        # Try to load a non-existent template
        missing_template = EmailTemplateEngine.load_template_from_file("templates/nonexistent_template.html")
        
        print("✅ Fallback template loaded successfully")
        print(f"📏 Fallback template size: {len(missing_template)} characters")
        print("ℹ️  This demonstrates the fallback mechanism when template files are missing")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")

def list_available_templates():
    """List all available templates"""
    print("\n" + "="*60)
    print("AVAILABLE EMAIL TEMPLATES")
    print("="*60)
    
    import os
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    
    if os.path.exists(templates_dir):
        html_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
        
        if html_files:
            print("📁 Templates directory: templates/")
            for template_file in html_files:
                template_path = os.path.join(templates_dir, template_file)
                size = os.path.getsize(template_path)
                print(f"  📄 {template_file} ({size:,} bytes)")
        else:
            print("❌ No HTML templates found in templates/ directory")
    else:
        print("❌ Templates directory not found")

def main():
    """Run all template demos"""
    print("🎨 EMAIL TEMPLATE SYSTEM DEMONSTRATION")
    print("="*60)
    print("This demo shows how HTML templates are loaded from separate files")
    print("instead of being embedded in the Python code.")
    
    # List available templates
    list_available_templates()
    
    # Demo different template loading methods
    demo_professional_template()
    demo_simple_template() 
    demo_custom_invitation_template()
    demo_config_file_reference()
    demo_template_fallback()
    
    print("\n" + "="*60)
    print("💡 TEMPLATE USAGE SUMMARY")
    print("="*60)
    print("✅ Templates are now stored as separate HTML files")
    print("✅ Easy to edit templates without touching Python code")
    print("✅ Templates can be referenced in config.json")
    print("✅ Fallback mechanism for missing templates")
    print("✅ Multiple template options available")
    
    print("\n📝 How to add new templates:")
    print("1. Create new .html file in templates/ directory")
    print("2. Use placeholder variables: {first_name}, {name}, {email}")
    print("3. Reference in code: EmailTemplateEngine.load_template_from_file('templates/your_template.html')")
    print("4. Or reference in config.json: 'TEMPLATE_FILE:templates/your_template.html'")

if __name__ == "__main__":
    main()