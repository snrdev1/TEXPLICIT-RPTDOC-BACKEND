# Password reset request
PASSWORD_RESET_REQUEST_MAILSUBJECT="Reset Your Texplicit2 Password"
PASSWORD_RESET_REQUEST_MAILBODY='''\
<p>
    Dear {name},
    <br/><br/>
    We have received a request to reset your password for your Texplicit2 account. If you did initiate this request, please follow the instructions below to reset your password. If you did not make this request, you can safely ignore this email and rest assured that your account is secure.
    <br/>
    <br/>
    To reset your password, please click on the following link: <a href="{link}" target="_blank">{link}</a>. This link will be valid for the next 24 hours.
    <br/>
    <br/>
    If you have any difficulties resetting your password or have any concerns about the security of your account, please contact us at support@texplicit2.com.
    <br/>
    <br/>
    Thank you for using Texplicit2. We are committed to keeping your account secure and providing you with the best possible experience.

    <br/><br/>
    Warm regards,
    <br/>
    {sender}
</p>\
'''

# KI Sent For Approval
KI_SEND_FOR_APPROVAL_MAILSUBJECT="Thank you for your contribution to Texplicit02"
KI_SEND_FOR_APPROVAL_MAILBODY='''\
<p>
    Dear {receiver},
    <br/><br/>
    We wanted to take a moment to thank you for your recent contribution to Texplicit02. We are thrilled to have you as part of our community and appreciate your effort in sharing your knowledge and resources with others. 
    <br/>
    <br/>
    Your requested knowledge item, {ki_title}, has been received and is currently undergoing a review process. Our team of experts is carefully reviewing the content to ensure it aligns with our guidelines and provides value to our community.
    <br/>
    <br/>
    We will notify you as soon as your contribution has been approved and is ready to be shared with the Texplicit02 community. In the meantime, you can continue to explore the platform and connect with others who are on their personal growth journeys.
    <br/>
    <br/>
    Thank you again for your support and for making Texplicit02 a vibrant and informative platform. If you have any questions or concerns, please don't hesitate to reach out to us at support@Texplicit02.com.

    <br/>
    Warm regards,
    <br/>
    {sender}
</p>\
'''

# KI Approved
KI_APPROVED_MAILSUBJECT="Your Knowledge Item Has Been Approved on Texplicit02"
KI_APPROVED_MAILBODY='''\
<p>
    Dear {receiver},
    <br/><br/>
    We are pleased to inform you that your knowledge item,{ki_title}, has been approved and is now available on Texplicit02 for the community to access and benefit from. 
    <br/>
    <br/>
    Your contribution to the platform is greatly appreciated and will help others on their personal growth journeys. We are committed to providing a platform where individuals can exchange ideas, share resources, and support each other, and your contribution is a testament to that commitment.
    <br/>
    <br/>
    We encourage you to share your knowledge item with others and participate in the community. If you have any questions or need assistance, please don't hesitate to reach out to us at support@Texplicit02.com.
    <br/>
    <br/>
    Thank you again for your support and for making Texplicit02 a vibrant and informative platform.
    <br/>
    <br/>
    Warm regards,
    <br/>
    {sender}
</p>\
'''

# KI Rejected
KI_REJECTED_MAILSUBJECT="Feedback on your Submission to Texplicit02"
KI_REJECTED_MAILBODY='''\
<p>
    Dear {receiver},
    <br/><br/>
    We wanted to provide you with feedback on your recent submission to Texplicit02, {ki_title}. After careful review, our team has decided not to approve your submission at this time.
    {reason}
    <br/>
    <br/>
    While we are unable to publish this particular submission, we appreciate your efforts in sharing your knowledge and resources with the community. Our goal is to provide a platform that supports personal growth and well-being, and our guidelines are in place to ensure that the content shared on Texplicit02 aligns with that goal.
    <br/>
    <br/>
    We encourage you to review our guidelines and consider submitting a revised version of your knowledge item in the future. If you have any questions or need assistance, please don't hesitate to reach out to us at support@Texplicit02.com.
    <br/>
    <br/>

    Thank you for your understanding and for your support of Texplicit02.

    <br/>
    Warm regards,
    <br/>
    {sender}
</p>\
'''