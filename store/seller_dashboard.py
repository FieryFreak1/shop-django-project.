from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import ProductListing


@login_required
def seller_dashboard(request):

    listings = (
        ProductListing.objects
        .filter(
            owner=request.user,
            seller_type="seller"
        )
        .select_related(
            "product",
            "product__details",
            "product__category",
        )
    )


    return render(
        request,
        "store/seller/dashboard.html",
        {
            "listings": listings,
        }
    )