from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['parent']


class CategoryWithChildrenView(generics.ListAPIView):
    queryset = Category.objects.filter(parent__isnull=True)
    serializer_class = CategoryWithChildrenSerializer


class AdViewSet(viewsets.ModelViewSet):
    queryset = Ad.objects.all()
    serializer_class = AdSerializer
    lookup_field = 'slug'
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return AdCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MyAdSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            # Filtering logic for ads list
            search = self.request.query_params.get('search')
            if search:
                queryset = queryset.filter(name__icontains=search)

            price_gte = self.request.query_params.get('price__gte')
            if price_gte:
                queryset = queryset.filter(price__gte=price_gte)

            price_lte = self.request.query_params.get('price__lte')
            if price_lte:
                queryset = queryset.filter(price__lte=price_lte)

            # Add more filters as needed
        return queryset


class MyAdViewSet(viewsets.ModelViewSet):
    serializer_class = MyAdSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Ad.objects.filter(seller=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class FavouriteProductViewSet(viewsets.ModelViewSet):
    serializer_class = FavouriteProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return FavouriteProduct.objects.filter(user=self.request.user)
        device_id = self.request.query_params.get('device_id')
        if device_id:
            return FavouriteProduct.objects.filter(device_id=device_id)
        return FavouriteProduct.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data['product'].id

        # Check if already exists
        exists = FavouriteProduct.objects.filter(
            user=request.user if request.user.is_authenticated else None,
            device_id=request.data.get('device_id'),
            product_id=product_id
        ).exists()

        if exists:
            return Response(
                {'detail': 'Product already in favourites'},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class MySearchViewSet(viewsets.ModelViewSet):
    serializer_class = MySearchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MySearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PopularSearchTermView(generics.ListAPIView):
    queryset = PopularSearchTerm.objects.order_by('-search_count')
    serializer_class = PopularSearchTermSerializer
    pagination_class = None

    def get_queryset(self):
        limit = self.request.query_params.get('limit')
        queryset = super().get_queryset()
        if limit:
            queryset = queryset[:int(limit)]
        return queryset


class SearchCountIncreaseView(generics.RetrieveAPIView):
    queryset = PopularSearchTerm.objects.all()
    serializer_class = PopularSearchTermSerializer
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.search_count += 1
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ProductDownloadView(generics.RetrieveAPIView):
    queryset = Ad.objects.all()
    serializer_class = AdSerializer
    lookup_field = 'slug'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # In a real implementation, you would generate a PDF here
        # For simplicity, we're just returning JSON
        return Response(serializer.data)


class ProductImageCreateView(generics.CreateAPIView):
    queryset = AdImage.objects.all()
    serializer_class = AdImageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        ad = get_object_or_404(Ad, pk=self.request.data.get('product_id'), seller=self.request.user)
        serializer.save(ad=ad)


class SearchCompleteView(generics.ListAPIView):
    serializer_class = AdSerializer

    def get_queryset(self):
        q = self.request.query_params.get('q', '')
        return Ad.objects.filter(name__icontains=q)[:10]
